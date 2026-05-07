"""AI consultation orchestrator (Phase 2 Wave B).

Wires together the four Wave B layers:
  - audit.get_render_detail (concept + lineage joins)
  - rubric.load_active_rubric (parsed rubric from docs/AUDIT_RUBRICS_v*.md)
  - thumbnails.get_or_generate (downscaled image for vision API per 4.8)
  - audit_providers.<provider>.call_vision (per-provider vision call)

Flow:
  1. Fetch render detail; 404 if missing.
  2. Load active rubric; 400 if no rubric authored yet (Wave A non-AI
     mode keeps working independently).
  3. Get downscaled image; 400 if file missing / unprocessable.
  4. Compose concept_text + lineage_summary from detail.
  5. For each requested provider: call_vision → VisionConsultationResponse.
  6. Find or auto-create verdict to attach consultations to:
       - if latest non-superseded verdict exists, attach to it
       - else: create a placeholder verdict using first completed
         response's verdict_inference; audited_by='multi_ai_assisted'
  7. Persist each consultation (state.db row + YAML at
     `_data/ai_consultations/<id>.yaml`).
  8. Update verdict.consultation_cost_usd via SUM over its
     ai_consultations rows.
  9. If audit_session_id provided: increment session's
     total_consultations + total_cost_usd.
  10. Return summary {render_id, verdict_id, consultations: [...],
                     total_cost_usd}.

SDK-level failures from the vision adapter (VisionError /
LLMError subclass) propagate; caller (the endpoint or test harness)
hands them to the retry queue mechanism the same way draft_via_api
does. Non-SDK status outcomes (parse_failed, safety_refused,
context_exceeded) are persisted as ai_consultations rows with
non-'completed' status — Joseph sees them in the audit-trail.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

import audit
import db
import llm
import rubric as rubric_mod
import thumbnails
from audit_providers import anthropic as anthropic_provider
from constants import CURRENT_DISCIPLINE_VERSION


PROVIDERS = {
    "anthropic": anthropic_provider,
    # Phase 2 Wave B Week 2 conditional: "perplexity": perplexity_provider
    # Phase 3: "chatgpt": chatgpt_provider, "gemini": gemini_provider
}


class ConsultationError(Exception):
    """Caller-facing setup error (missing render / rubric / image).
    Distinct from VisionError which wraps SDK failures."""


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _consultation_id_from(verdict_id: str, provider: str, api_call_id: str) -> str:
    """Stable derived ID. Multiple consultations against the same verdict
    + provider get distinct IDs via the api_call_id disambiguator."""
    return hashlib.sha256(
        f"{verdict_id}|{provider}|{api_call_id}".encode("utf-8")
    ).hexdigest()[:16]


def _consultations_dir() -> Path:
    return db.DATA_DIR / "ai_consultations"


def _write_consultation_yaml(record: dict) -> None:
    d = _consultations_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{record['id']}.yaml"
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, sort_keys=False,
                       default_flow_style=False, allow_unicode=True)
    tmp.replace(path)


def _build_concept_text(concept: Optional[dict]) -> Optional[str]:
    if not concept:
        return None
    parts: list[str] = []
    if concept.get("section"):
        parts.append(f"Section: {concept['section']}.")
    if concept.get("subject"):
        parts.append(f"Subject: {concept['subject']}.")
    if concept.get("register"):
        parts.append(f"Register: {concept['register']}.")
    if concept.get("name"):
        parts.append(f"Concept name: {concept['name']}.")
    return " ".join(parts) if parts else None


def _build_lineage_summary(edges: list[dict]) -> Optional[str]:
    if not edges:
        return None
    # Cap at 10 most-recent edges to keep prompt size bounded (4.11
    # context-exceeded mitigation; full lineage is in db for the
    # fallback-to-truncated path the adapter would invoke if needed).
    capped = edges[:10]
    lines = [
        f"layer={e['layer']}: {e['source_type']}:{e['source_id']} "
        f"-> {e['target_type']}:{e['target_id']}"
        for e in capped
    ]
    summary = "\n".join(lines)
    if len(edges) > 10:
        summary += f"\n... ({len(edges) - 10} more edges omitted)"
    return summary


def consult_render(
    render_id: str, *,
    audit_session_id: Optional[str] = None,
    providers: Optional[list[str]] = None,
    repo_root: Optional[Path] = None,
) -> dict:
    """Run AI consultation against a render. See module docstring for flow.

    Raises:
      ConsultationError on setup-level issues (missing render, rubric,
        image, unknown provider).
      VisionError (LLMError subclass) on SDK-level failures (rate limit,
        auth, timeout, etc.).
    """
    if providers is None:
        providers = ["anthropic"]
    if repo_root is None:
        repo_root = db.TOOL_BUILD_DIR.parent.parent.parent

    for p in providers:
        if p not in PROVIDERS:
            raise ConsultationError(
                f"unknown provider {p!r}; available: {sorted(PROVIDERS)}"
            )

    # 1. Render detail
    detail = audit.get_render_detail(render_id)
    if detail is None:
        raise ConsultationError(f"render {render_id!r} not found")

    # 2. Rubric
    parsed_rubric = rubric_mod.load_active_rubric(repo_root)
    if parsed_rubric is None:
        raise ConsultationError(
            "no audit rubric available; author "
            "docs/AUDIT_RUBRICS_v1_0.md before running consultations "
            "(Wave A verdict capture continues to work without it)"
        )

    # 3. Image
    thumb = thumbnails.get_or_generate(render_id)
    if thumb is None:
        raise ConsultationError(
            f"could not produce thumbnail for render {render_id!r} "
            "(file missing or unprocessable)"
        )
    image_path = thumb["thumbnail_abs_path"]
    used_downscale = True

    # 4. Compose context
    concept_text = _build_concept_text(detail.get("concept"))
    lineage_summary = _build_lineage_summary(detail.get("lineage_edges", []))

    # 5. Call providers (sequential per Q4 default)
    raw_responses: list[tuple[str, Any]] = []
    for p_name in providers:
        provider_module = PROVIDERS[p_name]
        resp = provider_module.call_vision(
            image_path=image_path, rubric=parsed_rubric,
            concept_text=concept_text, lineage_summary=lineage_summary,
            used_downscale=used_downscale,
        )
        raw_responses.append((p_name, resp))

    # 6. Find-or-create verdict
    verdict_id: Optional[str] = None
    if detail.get("verdict"):
        verdict_id = detail["verdict"]["id"]
        auto_created_verdict = False
    else:
        first_completed = next(
            (r for _, r in raw_responses if r.status == "completed" and r.parsed),
            None,
        )
        if first_completed is None:
            # No usable inference; persist consultations with no verdict?
            # ai_consultations.verdict_id is NOT NULL — we can't. Force
            # a placeholder verdict with verdict='weak' as the safest
            # default (Joseph can supersede after reviewing).
            placeholder = audit.capture_verdict(
                render_id=render_id, verdict="weak",
                verdict_reasoning=(
                    "Auto-created placeholder; AI consultations did not "
                    "complete. Supersede with manual verdict after review."
                ),
                audited_by="multi_ai_assisted",
                audit_session_id=audit_session_id,
                rubric_version=parsed_rubric["version"],
            )
            verdict_id = placeholder["id"]
            auto_created_verdict = True
        else:
            inference = first_completed.parsed.get("verdict_inference") or "weak"
            if inference not in audit.VERDICT_VALUES:
                inference = "weak"
            placeholder = audit.capture_verdict(
                render_id=render_id, verdict=inference,
                verdict_reasoning=(
                    f"Auto-created from {raw_responses[0][0]} consultation; "
                    "Joseph supersedes if disagreeing."
                ),
                audited_by="multi_ai_assisted",
                audit_session_id=audit_session_id,
                rubric_version=parsed_rubric["version"],
            )
            verdict_id = placeholder["id"]
            auto_created_verdict = True

    # 7. Persist each consultation as state.db row + YAML
    persisted: list[dict] = []
    total_cost = 0.0
    for p_name, resp in raw_responses:
        consult_id = _consultation_id_from(verdict_id, p_name, resp.api_call_id)
        yaml_rel = (
            f"projects/latent_systems/tool_build/_data/ai_consultations/"
            f"{consult_id}.yaml"
        )
        consulted_at = _iso_now()
        record = {
            "id": consult_id,
            "verdict_id": verdict_id,
            "discipline_version": CURRENT_DISCIPLINE_VERSION,
            "provider": p_name,
            "model": resp.model,
            "consulted_at": consulted_at,
            "status": resp.status,
            "cost_usd": resp.cost_usd,
            "used_downscale": resp.used_downscale,
            "raw_response": resp.raw_response,
            "parsed": resp.parsed,
            "failure_reason": resp.failure_reason,
            "api_call_id": resp.api_call_id,
            "yaml_path": yaml_rel,
        }
        _write_consultation_yaml(record)

        conn = db.connect()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO ai_consultations (
                        id, verdict_id, provider, model, consulted_at,
                        status, cost_usd, used_downscale, raw_response,
                        parsed_json, failure_reason, yaml_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        consult_id, verdict_id, p_name, resp.model, consulted_at,
                        resp.status, resp.cost_usd,
                        1 if resp.used_downscale else 0, resp.raw_response,
                        json.dumps(resp.parsed) if resp.parsed else None,
                        resp.failure_reason, yaml_rel,
                    ),
                )
        finally:
            conn.close()
        persisted.append(record)
        total_cost += resp.cost_usd

    # 8. Update verdict.consultation_cost_usd via SUM, plus session
    # rollups when an audit_session is in scope.
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                UPDATE verdicts SET consultation_cost_usd = (
                    SELECT COALESCE(SUM(cost_usd), 0)
                    FROM ai_consultations WHERE verdict_id = ?
                ) WHERE id = ?
                """,
                (verdict_id, verdict_id),
            )
            if audit_session_id is not None:
                conn.execute(
                    """
                    UPDATE audit_sessions SET
                        total_consultations = total_consultations + ?,
                        total_cost_usd = total_cost_usd + ?
                    WHERE id = ?
                    """,
                    (len(persisted), total_cost, audit_session_id),
                )
    finally:
        conn.close()

    return {
        "render_id": render_id,
        "verdict_id": verdict_id,
        "auto_created_verdict": auto_created_verdict,
        "consultations": persisted,
        "total_cost_usd": total_cost,
    }
