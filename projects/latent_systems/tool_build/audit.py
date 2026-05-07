"""Audit viewer business logic (Phase 2 Wave A).

Per phase2_design_notes.md v0.4 §1-§5 + Migration 0003 schema.

Wave A scope (this module):
  - Audit session lifecycle (create / list / end)
  - Render detail joins (concept + lineage + latest verdict)
  - Verdict capture (instant filesystem write per F8 4.9 — never lose
    a verdict to UI race; YAML before SQL so failed YAML leaves no
    orphan db row)
  - Verdict flag toggles (needs_second_look only per Q3 minimal scope)
  - Audit queue with composable filters (tool / section / flagged /
    needs-review-paths / unverdicted)
  - Session cost rollup (Wave A returns $0; Wave B layers AI consultation
    costs into the rollup)

Wave B will add: AI consultation invocation, multi-AI provider fanout,
rubric-driven evaluation. ai_consultations table exists from Migration
0003 but is not populated in Wave A.

Pattern conventions (mirror dispatcher.create_concept):
  - Validate inputs (raise ValueError on invalid; endpoint wraps as
    HTTPException 400)
  - sha256(content|timestamp)[:16] ID derivation for stable IDs
  - YAML write BEFORE SQL insert — failed YAML leaves no orphan row
  - All connection lifecycle via db.connect() (Pattern #3 codec setup
    happens via the import db at module load)
  - discipline_version defaults to CURRENT_DISCIPLINE_VERSION
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

import db
from constants import CURRENT_DISCIPLINE_VERSION


# Valid verdict commitments per design notes §3 (4-bucket enum;
# practical extensions ride on flags, not a 5th status).
VERDICT_VALUES = frozenset({"hero_zone", "strong", "weak", "reject"})

# Audit session UI mode (per Q5 storage decision: persist on
# audit_sessions.mode column; new session defaults to last-used mode
# fetched at the endpoint layer).
SESSION_MODES = frozenset({"quick_pass", "deep_eval"})

# Audited-by attribution values (record who/what marked the verdict).
AUDITED_BY_VALUES = frozenset({
    "human", "claude_assisted", "multi_ai_assisted",
})


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit_session_id_from(rubric_version: str, mode: str, iso: str) -> str:
    return hashlib.sha256(
        f"{rubric_version}|{mode}|{iso}".encode("utf-8")
    ).hexdigest()[:16]


def _verdict_id_from(render_id: str, iso: str) -> str:
    return hashlib.sha256(
        f"{render_id}|{iso}".encode("utf-8")
    ).hexdigest()[:16]


def _audit_sessions_dir() -> Path:
    return db.DATA_DIR / "audit_sessions"


def _verdicts_dir() -> Path:
    return db.DATA_DIR / "verdicts"


def _write_yaml(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, sort_keys=False,
                       default_flow_style=False, allow_unicode=True)
    tmp.replace(path)  # atomic rename — partial writes never visible


# ----------------------------------------------------------------------
# Audit sessions
# ----------------------------------------------------------------------

def create_audit_session(
    *,
    rubric_version: str = "1.0",
    mode: str = "quick_pass",
    scope_concept_id: Optional[str] = None,
    scope_section: Optional[str] = None,
    scope_filter: Optional[dict] = None,
    notes: Optional[str] = None,
) -> dict:
    """Create a new audit session. Returns the new record.

    Validates mode + scope_concept_id (must exist if provided).
    `scope_filter` (dict) is JSON-serialized into scope_filter_json.
    """
    if mode not in SESSION_MODES:
        raise ValueError(
            f"invalid mode {mode!r}; expected one of {sorted(SESSION_MODES)}"
        )
    conn = db.connect()
    try:
        if scope_concept_id is not None:
            row = conn.execute(
                "SELECT id FROM concepts WHERE id = ?", (scope_concept_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"concept {scope_concept_id!r} not found")
    finally:
        conn.close()

    now = _iso_now()
    session_id = _audit_session_id_from(rubric_version, mode, now)
    yaml_path = (
        f"projects/latent_systems/tool_build/_data/audit_sessions/"
        f"{session_id}.yaml"
    )
    scope_filter_json = json.dumps(scope_filter) if scope_filter else None

    record = {
        "id": session_id,
        "started": now,
        "ended": None,
        "rubric_version": rubric_version,
        "discipline_version": CURRENT_DISCIPLINE_VERSION,
        "mode": mode,
        "scope_concept_id": scope_concept_id,
        "scope_section": scope_section,
        "scope_filter": scope_filter,
        "total_consultations": 0,
        "total_cost_usd": 0.0,
        "notes": notes,
        "yaml_path": yaml_path,
    }
    _write_yaml(_audit_sessions_dir() / f"{session_id}.yaml", record)

    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO audit_sessions (
                    id, started, ended, rubric_version, discipline_version,
                    mode, scope_concept_id, scope_section, scope_filter_json,
                    total_consultations, total_cost_usd, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, now, None, rubric_version,
                 CURRENT_DISCIPLINE_VERSION, mode,
                 scope_concept_id, scope_section, scope_filter_json,
                 0, 0.0, notes),
            )
    finally:
        conn.close()
    return record


def list_audit_sessions(*, limit: int = 50, active_only: bool = False) -> list[dict]:
    """List sessions, newest first. active_only=True filters to ended IS NULL."""
    conn = db.connect()
    try:
        where = "WHERE ended IS NULL" if active_only else ""
        rows = conn.execute(
            f"""
            SELECT id, started, ended, rubric_version, discipline_version,
                   mode, scope_concept_id, scope_section, scope_filter_json,
                   total_consultations, total_cost_usd, notes
            FROM audit_sessions {where}
            ORDER BY started DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_session(r) for r in rows]


def get_audit_session(session_id: str) -> Optional[dict]:
    conn = db.connect()
    try:
        row = conn.execute(
            """
            SELECT id, started, ended, rubric_version, discipline_version,
                   mode, scope_concept_id, scope_section, scope_filter_json,
                   total_consultations, total_cost_usd, notes
            FROM audit_sessions WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_session(row) if row else None


def end_audit_session(session_id: str) -> dict:
    """Mark a session as ended. Idempotent: re-ending preserves the
    original ended timestamp."""
    now = _iso_now()
    conn = db.connect()
    try:
        existing = conn.execute(
            "SELECT id, ended FROM audit_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if existing is None:
            raise ValueError(f"audit_session {session_id!r} not found")
        if existing[1] is not None:
            # Already ended — return current state without overwriting.
            return get_audit_session(session_id)  # type: ignore[return-value]
        with conn:
            conn.execute(
                "UPDATE audit_sessions SET ended = ? WHERE id = ?",
                (now, session_id),
            )
    finally:
        conn.close()
    return get_audit_session(session_id)  # type: ignore[return-value]


def _row_to_session(row) -> dict:
    return {
        "id": row[0], "started": row[1], "ended": row[2],
        "rubric_version": row[3], "discipline_version": row[4],
        "mode": row[5],
        "scope_concept_id": row[6], "scope_section": row[7],
        "scope_filter": json.loads(row[8]) if row[8] else None,
        "total_consultations": row[9], "total_cost_usd": row[10],
        "notes": row[11],
    }


# ----------------------------------------------------------------------
# Render detail
# ----------------------------------------------------------------------

def get_render_detail(render_id: str) -> Optional[dict]:
    """Return render + concept + latest non-superseded verdict + lineage edges.

    Joins: renders -> prompts -> concepts (when prompt_id is set);
    verdicts (latest non-superseded);
    lineage_edges where source_id = render_id OR target_id = render_id.
    """
    conn = db.connect()
    try:
        row = conn.execute(
            """
            SELECT id, attempt_id, prompt_id, filename, filepath,
                   canonical_hash, tool, variant, hero_status,
                   discipline_version, yaml_path, created
            FROM renders WHERE id = ?
            """,
            (render_id,),
        ).fetchone()
        if row is None:
            return None
        record = {
            "id": row[0], "attempt_id": row[1], "prompt_id": row[2],
            "filename": row[3], "filepath": row[4],
            "canonical_hash": row[5], "tool": row[6], "variant": row[7],
            "hero_status": row[8], "discipline_version": row[9],
            "yaml_path": row[10], "created": row[11],
        }

        # Concept (joined via prompts.concept_id when prompt_id is set).
        record["concept"] = None
        if record["prompt_id"]:
            crow = conn.execute(
                """
                SELECT c.id, c.name, c.ep, c.section, c.subject, c.register, c.status
                FROM concepts c JOIN prompts p ON p.concept_id = c.id
                WHERE p.id = ?
                """,
                (record["prompt_id"],),
            ).fetchone()
            if crow:
                record["concept"] = {
                    "id": crow[0], "name": crow[1], "ep": crow[2],
                    "section": crow[3], "subject": crow[4],
                    "register": crow[5], "status": crow[6],
                }

        # Latest non-superseded verdict (a verdict V is superseded if
        # any other verdict X has supersedes_verdict_id = V.id).
        vrow = conn.execute(
            """
            SELECT v.id, v.verdict, v.audited_by, v.rubric_version,
                   v.flags_needs_second_look, v.audit_session_id,
                   v.consultation_cost_usd, v.created
            FROM verdicts v
            WHERE v.render_id = ?
              AND v.id NOT IN (
                  SELECT supersedes_verdict_id FROM verdicts
                  WHERE supersedes_verdict_id IS NOT NULL
              )
            ORDER BY v.created DESC LIMIT 1
            """,
            (render_id,),
        ).fetchone()
        record["verdict"] = (
            {
                "id": vrow[0], "verdict": vrow[1], "audited_by": vrow[2],
                "rubric_version": vrow[3],
                "flags_needs_second_look": bool(vrow[4]),
                "audit_session_id": vrow[5],
                "consultation_cost_usd": vrow[6], "created": vrow[7],
            }
            if vrow else None
        )

        # Lineage edges (incoming + outgoing; layer ascending then created).
        erows = conn.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id,
                   layer, valid_from_version, valid_to_version,
                   stale_reason, created
            FROM lineage_edges
            WHERE source_id = ? OR target_id = ?
            ORDER BY layer ASC, created ASC
            """,
            (render_id, render_id),
        ).fetchall()
        record["lineage_edges"] = [
            {
                "id": e[0], "source_type": e[1], "source_id": e[2],
                "target_type": e[3], "target_id": e[4], "layer": e[5],
                "valid_from_version": e[6], "valid_to_version": e[7],
                "stale_reason": e[8], "created": e[9],
            }
            for e in erows
        ]

        # Existing AI consultations for the latest verdict. Surfaced so
        # the audit viewer's consultation panel shows prior runs without
        # re-firing the API. Phase 2.5 enhancement per phase2_design_notes
        # v0.4 §3 ai_consultations table.
        record["ai_consultations"] = []
        if record["verdict"] is not None:
            crows = conn.execute(
                """
                SELECT id, provider, model, consulted_at, status, cost_usd,
                       used_downscale, raw_response, parsed_json,
                       failure_reason
                FROM ai_consultations
                WHERE verdict_id = ?
                ORDER BY consulted_at DESC
                """,
                (record["verdict"]["id"],),
            ).fetchall()
            for c in crows:
                parsed = None
                if c[8]:
                    try:
                        parsed = json.loads(c[8])
                    except json.JSONDecodeError:
                        parsed = None
                record["ai_consultations"].append({
                    "id": c[0],
                    "provider": c[1],
                    "model": c[2],
                    "consulted_at": c[3],
                    "status": c[4],
                    "cost_usd": c[5],
                    "used_downscale": bool(c[6]),
                    "raw_response": c[7],
                    "parsed": parsed,
                    "failure_reason": c[9],
                })
        return record
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Verdict capture (instant write per F8 4.9)
# ----------------------------------------------------------------------

def capture_verdict(
    *,
    render_id: str,
    verdict: str,
    verdict_reasoning: Optional[str] = None,
    audited_by: str = "human",
    audit_session_id: Optional[str] = None,
    rubric_version: Optional[str] = None,
    rubric_used: Optional[str] = None,
    rubric_criteria_match: Optional[dict] = None,
    flags_needs_second_look: bool = False,
    supersedes_verdict_id: Optional[str] = None,
) -> dict:
    """Capture a verdict against a render. Instant filesystem write per
    F8 success criterion 5 (no save button; verdict durable from moment
    of marking).

    Validates: verdict in VERDICT_VALUES; audited_by in AUDITED_BY_VALUES;
    render exists; audit_session exists if provided; supersedes_verdict
    exists if provided.

    Returns the new record. YAML written before SQL insert per
    project convention.
    """
    if verdict not in VERDICT_VALUES:
        raise ValueError(
            f"invalid verdict {verdict!r}; expected one of {sorted(VERDICT_VALUES)}"
        )
    if audited_by not in AUDITED_BY_VALUES:
        raise ValueError(
            f"invalid audited_by {audited_by!r}; expected one of {sorted(AUDITED_BY_VALUES)}"
        )

    conn = db.connect()
    try:
        if conn.execute(
            "SELECT id FROM renders WHERE id = ?", (render_id,)
        ).fetchone() is None:
            raise ValueError(f"render {render_id!r} not found")
        if audit_session_id is not None:
            if conn.execute(
                "SELECT id FROM audit_sessions WHERE id = ?", (audit_session_id,)
            ).fetchone() is None:
                raise ValueError(f"audit_session {audit_session_id!r} not found")
        if supersedes_verdict_id is not None:
            if conn.execute(
                "SELECT id FROM verdicts WHERE id = ?", (supersedes_verdict_id,)
            ).fetchone() is None:
                raise ValueError(
                    f"superseded verdict {supersedes_verdict_id!r} not found"
                )
    finally:
        conn.close()

    now = _iso_now()
    verdict_id = _verdict_id_from(render_id, now)
    yaml_path = (
        f"projects/latent_systems/tool_build/_data/verdicts/{verdict_id}.yaml"
    )

    record = {
        "id": verdict_id,
        "render_id": render_id,
        "discipline_version": CURRENT_DISCIPLINE_VERSION,
        "verdict": verdict,
        "verdict_reasoning": verdict_reasoning,
        "rubric_version": rubric_version,
        "rubric_used": rubric_used,
        "rubric_criteria_match": rubric_criteria_match,
        "audit_session_id": audit_session_id,
        "audited_by": audited_by,
        "flags": {"needs_second_look": flags_needs_second_look},
        "supersedes_verdict_id": supersedes_verdict_id,
        "ai_consultation_ids": [],  # Wave B will populate
        "yaml_path": yaml_path,
        "created": now,
    }
    _write_yaml(_verdicts_dir() / f"{verdict_id}.yaml", record)

    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO verdicts (
                    id, render_id, rubric_used, rubric_version, verdict,
                    audited_by, audit_session_id, consultation_cost_usd,
                    flags_needs_second_look, supersedes_verdict_id,
                    discipline_version, yaml_path, created
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (verdict_id, render_id, rubric_used, rubric_version, verdict,
                 audited_by, audit_session_id, 0.0,
                 1 if flags_needs_second_look else 0, supersedes_verdict_id,
                 CURRENT_DISCIPLINE_VERSION, yaml_path, now),
            )
    finally:
        conn.close()
    return record


def update_verdict_flags(
    verdict_id: str, *, needs_second_look: Optional[bool] = None,
) -> dict:
    """Toggle verdict flags. Currently supports needs_second_look only.
    Returns the updated verdict record (db row, not full YAML payload).

    YAML rewrite intentionally NOT done here: flags are a runtime
    triage signal, not a verdict commitment. State.db is sufficient.
    If Wave A use surfaces friction (e.g., YAML drift), promote to
    YAML-rewrite in Wave B.
    """
    if needs_second_look is None:
        raise ValueError("update_verdict_flags requires at least one flag")

    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT id FROM verdicts WHERE id = ?", (verdict_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"verdict {verdict_id!r} not found")
        with conn:
            conn.execute(
                "UPDATE verdicts SET flags_needs_second_look = ? WHERE id = ?",
                (1 if needs_second_look else 0, verdict_id),
            )
        updated = conn.execute(
            """
            SELECT id, render_id, verdict, audited_by, audit_session_id,
                   flags_needs_second_look, supersedes_verdict_id, created
            FROM verdicts WHERE id = ?
            """,
            (verdict_id,),
        ).fetchone()
    finally:
        conn.close()
    return {
        "id": updated[0], "render_id": updated[1], "verdict": updated[2],
        "audited_by": updated[3], "audit_session_id": updated[4],
        "flags_needs_second_look": bool(updated[5]),
        "supersedes_verdict_id": updated[6], "created": updated[7],
    }


# ----------------------------------------------------------------------
# Audit queue
# ----------------------------------------------------------------------

def list_audit_queue(
    *,
    only_unverdicted: bool = False,
    tool_filter: Optional[str] = None,
    section_filter: Optional[str] = None,
    flagged_only: bool = False,
    needs_review_paths: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return ordered list of renders for audit queue. All filters compose.

      - only_unverdicted: renders with no verdict at all
      - tool_filter: exact match on tool column
      - section_filter: filepath substring match (e.g. 'h5_slot_machine')
      - flagged_only: renders with at least one needs_second_look=1 verdict
      - needs_review_paths: renders under _unclassified/ or _inbox/

    Returns {total, limit, offset, items: [...]}. Default order: newest first.
    """
    where: list[str] = []
    params: list[Any] = []
    if only_unverdicted:
        # Any verdict — even superseded — counts as "verdicted" for the
        # queue. Re-audit happens via supersedes_verdict_id mechanism;
        # this filter is for "never been audited at all."
        where.append("id NOT IN (SELECT DISTINCT render_id FROM verdicts)")
    if tool_filter is not None:
        where.append("tool = ?")
        params.append(tool_filter)
    if section_filter is not None:
        where.append("filepath LIKE ?")
        params.append(f"%/{section_filter}/%")
    if flagged_only:
        where.append(
            "id IN (SELECT DISTINCT render_id FROM verdicts "
            "WHERE flags_needs_second_look = 1)"
        )
    if needs_review_paths:
        where.append(
            "(filepath LIKE '%_unclassified%' OR filepath LIKE '%_inbox%')"
        )
    where_clause = "WHERE " + " AND ".join(where) if where else ""

    conn = db.connect()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM renders {where_clause}", tuple(params)
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT id, filename, filepath, tool, variant, hero_status,
                   discipline_version, created
            FROM renders {where_clause}
            ORDER BY created DESC LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        ).fetchall()
    finally:
        conn.close()

    return {
        "total": total, "limit": limit, "offset": offset,
        "items": [
            {
                "render_id": r[0], "filename": r[1], "filepath": r[2],
                "tool": r[3], "variant": r[4], "hero_status": r[5],
                "discipline_version": r[6], "created": r[7],
            }
            for r in rows
        ],
    }


# ----------------------------------------------------------------------
# Cost rollup
# ----------------------------------------------------------------------

def get_session_cost(session_id: str) -> Optional[dict]:
    """Cost rollup for a session. Wave A returns $0 (no consultations);
    Wave B layers AI consultation costs into total_cost_usd."""
    conn = db.connect()
    try:
        row = conn.execute(
            """
            SELECT id, started, ended, total_consultations, total_cost_usd
            FROM audit_sessions WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        verdict_count = conn.execute(
            "SELECT COUNT(*) FROM verdicts WHERE audit_session_id = ?",
            (session_id,),
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "session_id": row[0],
        "started": row[1], "ended": row[2],
        "verdict_count": verdict_count,
        "total_consultations": row[3],
        "total_cost_usd": row[4],
    }
