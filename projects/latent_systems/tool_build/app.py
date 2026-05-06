"""FastAPI application for latent_systems tool_build v1.

Phase 1 ships with one endpoint (/healthz) so the server can be started
and verified end-to-end. Business endpoints — concept browser, prompt
drafting, audit viewer, etc. — land in Weeks 2-4 per Section 8.

Lifespan management (PID file, shutdown-file watcher) lives in
runtime.py; this module is just the FastAPI app definition so it can be
imported by uvicorn or by tests independently.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import db
import dispatcher


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(SCRIPT_DIR / "templates"))


app = FastAPI(title="latent_systems tool_build", version="0.1.0")


class PromptCreate(BaseModel):
    text: str
    tool: str = "midjourney"
    concept_id: Optional[str] = None


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    """Liveness + schema-version check. Returns ok if state.db is reachable
    and schema_version matches what this build expects."""
    payload: dict[str, Any] = {"status": "ok"}
    try:
        with db.connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_meta WHERE key='schema_version'"
            ).fetchone()
            payload["schema_version"] = row[0] if row else None
            payload["journal_mode"] = db.journal_mode(conn)
    except (FileNotFoundError, sqlite3.Error) as e:
        payload["status"] = "degraded"
        payload["error"] = str(e)
    # Watcher liveness — degraded but not failing if not running.
    try:
        import runtime
        w = runtime.get_download_watcher()
        payload["watcher"] = {
            "running": w is not None,
            "downloads_path": str(w.downloads_path) if w else None,
            "pending_count": len(w.pending()) if w else 0,
        }
    except Exception as e:
        payload["watcher"] = {"running": False, "error": str(e)}
    return payload


@app.get("/pending_downloads")
def pending_downloads() -> dict[str, Any]:
    """Inspect the watcher's hash-tracking state. Returns the persisted
    pending_downloads.json content or a not-running marker."""
    try:
        import runtime
        w = runtime.get_download_watcher()
    except Exception as e:
        return {"running": False, "error": str(e)}
    if w is None:
        return {"running": False, "pending": {}}
    return {
        "running": True,
        "downloads_path": str(w.downloads_path),
        "pending": w.pending(),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Minimal HTML UI for prompt drafting + dispatch (Day 7)."""
    return TEMPLATES.TemplateResponse("index.html", {"request": request})


@app.get("/prompts")
def list_prompts_endpoint(limit: int = 50) -> dict[str, Any]:
    """List recent prompts ordered by creation desc."""
    return {"prompts": dispatcher.list_prompts(limit=limit)}


@app.post("/prompts", status_code=201)
def create_prompt_endpoint(body: PromptCreate) -> dict[str, Any]:
    """Create a draft prompt. Returns the new record."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="prompt text is required")
    if body.tool not in dispatcher.TOOL_URLS:
        raise HTTPException(status_code=400,
                            detail=f"tool '{body.tool}' not supported (have: {sorted(dispatcher.TOOL_URLS.keys())})")
    return dispatcher.create_prompt(
        prompt_text=body.text, tool=body.tool, concept_id=body.concept_id,
    )


@app.post("/prompts/{prompt_id}/dispatch")
def dispatch_prompt_endpoint(prompt_id: str) -> dict[str, Any]:
    """Lock + create generation_attempt + clipboard write + browser open."""
    text = dispatcher.get_prompt_text(prompt_id)
    if text is None:
        raise HTTPException(status_code=404, detail=f"prompt {prompt_id} not found")
    # Look up tool from db.
    with db.connect() as conn:
        row = conn.execute("SELECT tool FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"prompt {prompt_id} missing in db")
    tool = row[0]
    return dispatcher.dispatch(prompt_id=prompt_id, prompt_text=text, tool=tool)


# --- Day 8 — failure modes 3b.1, 3b.2, 3b.4 (aging) and 3b.5 (inbox) ---


class FailReason(BaseModel):
    reason: str


class CompleteNote(BaseModel):
    note: Optional[str] = None


@app.get("/prompts/awaiting")
def awaiting_prompts_endpoint() -> dict[str, Any]:
    """List awaiting-return prompts with derived attempt aging.

    Each attempt has age_status one of:
        in_flight (< 30min), still_waiting (30min-24h), stale_check (>= 24h),
        closed (attempt no longer in_flight).
    """
    return {"prompts": dispatcher.awaiting_prompts()}


@app.post("/attempts/{attempt_id}/manual_complete")
def manual_complete_endpoint(attempt_id: str, body: Optional[CompleteNote] = None) -> dict[str, Any]:
    """Mark attempt completed without binding to a render (Day 9 owns binding).
    For when the generation worked but auto-detection didn't fire."""
    note = body.note if body else None
    result = dispatcher.manual_complete_attempt(attempt_id, note=note)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "unknown"))
    return result


@app.post("/attempts/{attempt_id}/mark_failed")
def mark_failed_endpoint(attempt_id: str, body: FailReason) -> dict[str, Any]:
    """Mark attempt failed with reason. Promotes prompt to 'failed' if no
    other in-flight attempts; else prompt stays 'awaiting_return'."""
    if not body.reason.strip():
        raise HTTPException(status_code=400, detail="reason is required")
    result = dispatcher.mark_attempt_failed(attempt_id, body.reason)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "unknown"))
    return result


@app.post("/attempts/{attempt_id}/kick")
def kick_endpoint(attempt_id: str) -> dict[str, Any]:
    """'Still waiting' — reset the started timer for aging recomputation."""
    result = dispatcher.kick_attempt(attempt_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "unknown"))
    return result


@app.get("/inbox_renders")
def inbox_renders_endpoint(limit: int = 50) -> dict[str, Any]:
    """Surface low-confidence routes (3b.5). These need user review to
    determine final canonical destination."""
    return {"renders": dispatcher.inbox_renders(limit=limit)}


# --- Day 9 — render binding (Feature 3b loop close) ---


class BindRequest(BaseModel):
    attempt_id: str
    force: bool = False


class OrphanNote(BaseModel):
    note: Optional[str] = None


@app.get("/unbound_renders")
def unbound_renders_endpoint(limit: int = 100) -> dict[str, Any]:
    """List post-v1 renders that arrived via router but didn't auto-bind.
    Includes needs_review_reason + suggested candidate when available."""
    return {
        "renders": dispatcher.unbound_renders(limit=limit),
        "open_attempts": dispatcher.open_attempts(),
    }


@app.post("/renders/{render_id}/bind")
def bind_render_endpoint(render_id: str, body: BindRequest) -> dict[str, Any]:
    """Manual bind. Used for orphan reconciliation (3b.6 picker), tool-
    mismatch override (3b.3 'bind anyway'), or post-Day-8 manual_complete
    cleanup."""
    result = dispatcher.bind_render_to_attempt(
        render_id, body.attempt_id, force=body.force,
    )
    if not result.get("ok"):
        # tool_mismatch returns ok=False but is recoverable via force=true.
        # Surface it as 409 (conflict) so the UI can prompt for confirmation.
        if result.get("error") == "tool_mismatch":
            raise HTTPException(status_code=409, detail=result)
        raise HTTPException(status_code=400, detail=result.get("error", "unknown"))
    return result


@app.post("/renders/{render_id}/mark_orphan")
def mark_orphan_endpoint(render_id: str, body: Optional[OrphanNote] = None) -> dict[str, Any]:
    """Explicitly stamp a render as orphan. For renders confirmed not-from-v1."""
    note = body.note if body else None
    return dispatcher.mark_render_orphan(render_id, note=note)


# --- Day 11 Week 3 — API-driven prompt drafting (Feature 2 via Claude API) ---


class DraftRequest(BaseModel):
    concept_text: str
    tool: str = "midjourney"
    concept_id: Optional[str] = None


@app.get("/retry_queue")
def retry_queue_endpoint() -> dict[str, Any]:
    """Snapshot of the current retry queue + last processor tick summary."""
    import retry_queue
    payload: dict[str, Any] = {"queue": retry_queue.list_queue()}
    try:
        import runtime
        payload["last_processor_tick"] = runtime.get_last_retry_processor_summary()
    except Exception as e:
        payload["last_processor_tick"] = {"error": str(e)}
    return payload


@app.post("/retry_queue/{prompt_id}/cancel")
def retry_queue_cancel_endpoint(prompt_id: str) -> dict[str, Any]:
    """Remove a prompt from the auto-retry queue and mark it permanently
    failed. Used for manual escape from a retry loop."""
    import retry_queue
    removed = retry_queue.remove(prompt_id)
    if not removed:
        raise HTTPException(status_code=404,
                            detail=f"prompt {prompt_id} not in retry queue")
    with db.connect() as conn:
        conn.execute(
            "UPDATE prompts SET status = 'failed', "
            "failure_reason = COALESCE(failure_reason || ' | ', '') || 'cancelled by user' "
            "WHERE id = ?",
            (prompt_id,),
        )
        conn.commit()
    return {"ok": True, "prompt_id": prompt_id, "action": "cancelled"}


@app.post("/prompts/{prompt_id}/retry")
def retry_prompt_endpoint(prompt_id: str) -> dict[str, Any]:
    """Manual retry — for 3a.4 timeout, 3a.6 bad_request, or post-exhaust
    on 3a.1/3a.5. Reads concept_text from prompt YAML and re-issues the
    API call. Returns the same shape as draft_via_api on success."""
    result = dispatcher.retry_prompt(prompt_id)
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result)
    return result


@app.get("/api_status")
def api_status_endpoint() -> dict[str, Any]:
    """Lightweight health for UI banner: is ANTHROPIC_API_KEY configured?
    Recent auth failures? Recent rate-limit failures? Used to surface 3a.2
    auth-error modals + 3a.1 'rate-limited persistently' state.
    Day 13: includes rolling cost breakdown for the cost dashboard."""
    import os
    payload: dict[str, Any] = {
        "anthropic_key_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
    try:
        with db.connect() as conn:
            recent_auth = conn.execute(
                "SELECT COUNT(*) FROM api_calls "
                "WHERE status = 'auth_failed' "
                "AND started > datetime('now', '-1 hour')"
            ).fetchone()
            recent_rate = conn.execute(
                "SELECT COUNT(*) FROM api_calls "
                "WHERE status = 'rate_limited' "
                "AND started > datetime('now', '-1 hour')"
            ).fetchone()
            recent_succeeded = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(cost_usd_estimate), 0) FROM api_calls "
                "WHERE status = 'succeeded' "
                "AND started > datetime('now', '-1 hour')"
            ).fetchone()
        payload["recent_auth_failures_1h"] = recent_auth[0]
        payload["recent_rate_limited_1h"] = recent_rate[0]
        payload["recent_succeeded_1h"] = recent_succeeded[0]
        payload["recent_cost_usd_1h"] = round(recent_succeeded[1] or 0, 4)
        payload["banner"] = None
        if not payload["anthropic_key_configured"]:
            payload["banner"] = "ANTHROPIC_API_KEY not configured — set in .env and restart"
        elif recent_auth[0] > 0:
            payload["banner"] = "Anthropic auth failing — check ANTHROPIC_API_KEY in .env"
        elif recent_rate[0] >= 3:
            payload["banner"] = f"Rate limited persistently ({recent_rate[0]} times in last hour) — backoff active"
        # Day 13 — cost breakdown
        payload["cost_breakdown"] = dispatcher.cost_breakdown()
    except (FileNotFoundError, sqlite3.Error) as e:
        payload["error"] = str(e)
    return payload


# --- Day 14 — Feature 1: Concept CRUD + browser ---


class ConceptCreate(BaseModel):
    name: str
    ep: Optional[str] = None
    section: Optional[str] = None
    subject: Optional[str] = None
    register: Optional[str] = None
    status: str = "drafting"


class ConceptUpdate(BaseModel):
    name: Optional[str] = None
    ep: Optional[str] = None
    section: Optional[str] = None
    subject: Optional[str] = None
    register: Optional[str] = None
    status: Optional[str] = None


@app.post("/concepts", status_code=201)
def create_concept_endpoint(body: ConceptCreate) -> dict[str, Any]:
    """Create a new concept (Feature 1)."""
    try:
        return dispatcher.create_concept(
            name=body.name, ep=body.ep, section=body.section,
            subject=body.subject, register=body.register, status=body.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/concepts")
def list_concepts_endpoint(
    ep: Optional[str] = None, section: Optional[str] = None,
    status: Optional[str] = None, register: Optional[str] = None,
    include_archived: bool = False, limit: int = 200,
) -> dict[str, Any]:
    """Filtered list of concepts. Archived excluded unless include_archived=True."""
    return {
        "concepts": dispatcher.list_concepts(
            ep=ep, section=section, status=status, register=register,
            include_archived=include_archived, limit=limit,
        ),
    }


@app.get("/concepts/{concept_id}")
def get_concept_endpoint(concept_id: str) -> dict[str, Any]:
    """Concept detail with linked prompts, renders, verdicts, hero_promotions."""
    record = dispatcher.get_concept(concept_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"concept {concept_id} not found")
    return record


@app.patch("/concepts/{concept_id}")
def update_concept_endpoint(concept_id: str, body: ConceptUpdate) -> dict[str, Any]:
    """Update concept fields. Substantive edits bump discipline_version per F10."""
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()
              if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="no fields to update")
    try:
        return dispatcher.update_concept(concept_id, fields=fields)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@app.post("/concepts/{concept_id}/archive")
def archive_concept_endpoint(concept_id: str) -> dict[str, Any]:
    """Soft-archive: status='archived'. Excluded from default list."""
    try:
        return dispatcher.archive_concept(concept_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Day 15 — Phase 1 acceptance: F1 + F4 query endpoints ---


class LineageEdgeCreate(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    layer: int
    valid_from_version: Optional[str] = None


@app.get("/renders/{render_id}")
def get_render_endpoint(render_id: str) -> dict[str, Any]:
    """F1 satisfaction: full render detail with the prompt that produced
    it + the concept that informed the prompt. Recovery in <2s by render_id."""
    record = dispatcher.get_render_detail(render_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"render {render_id} not found")
    return record


@app.get("/lineage/{artifact_type}/{artifact_id}")
def lineage_endpoint(artifact_type: str, artifact_id: str) -> dict[str, Any]:
    """F4 satisfaction: incoming + outgoing lineage edges for an artifact.
    Outgoing = what this artifact cites as anchor.
    Incoming = what cites this artifact as anchor."""
    return dispatcher.lineage_for_artifact(artifact_type, artifact_id)


@app.post("/lineage_edges", status_code=201)
def create_lineage_edge_endpoint(body: LineageEdgeCreate) -> dict[str, Any]:
    """Create a lineage edge. Layer 1=render-render, 2=concept-concept,
    3=channel-arch→ep-arch→notes.md inheritance."""
    try:
        kwargs = {
            "source_type": body.source_type, "source_id": body.source_id,
            "target_type": body.target_type, "target_id": body.target_id,
            "layer": body.layer,
        }
        if body.valid_from_version:
            kwargs["valid_from_version"] = body.valid_from_version
        return dispatcher.create_lineage_edge(**kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Day 13 — Feature 9: discipline-drift query surface (per spec F10) ---


@app.get("/discipline_drift")
def discipline_drift_endpoint() -> dict[str, Any]:
    """Cross-artifact summary of discipline-version distribution. Status
    badge in UI uses `totals_by_version` to surface "N artifacts at v0.X"."""
    payload = dispatcher.discipline_drift_summary()
    payload["stale_lineage_edges"] = dispatcher.stale_lineage_edges()
    return payload


@app.get("/discipline_drift/version/{version}")
def discipline_drift_version_endpoint(version: str, limit_per_type: int = 100) -> dict[str, Any]:
    """Drill-down: all artifacts authored against a specific
    discipline_version. Returns concepts, prompts, renders, verdicts,
    hero_promotions, lineage_edges, cross_ai_captures."""
    return dispatcher.discipline_drift_artifacts(version, limit_per_type=limit_per_type)


@app.post("/prompts/draft_via_api")
def draft_via_api_endpoint(body: DraftRequest) -> dict[str, Any]:
    """Draft a tool-specific prompt via Claude API. Creates a prompts row
    with drafted_by=<model> + cost-tracked api_calls row. Returns the
    draft text + cost/latency metadata."""
    if not body.concept_text.strip():
        raise HTTPException(status_code=400, detail="concept_text is required")
    if body.tool not in dispatcher.TOOL_URLS:
        raise HTTPException(
            status_code=400,
            detail=f"tool '{body.tool}' not supported (have: {sorted(dispatcher.TOOL_URLS.keys())})",
        )
    try:
        return dispatcher.draft_via_api(
            concept_text=body.concept_text, tool=body.tool,
            concept_id=body.concept_id,
        )
    except Exception as e:
        # llm.LLMError or anything else — surface as 502 (upstream) for retryable,
        # 500 for non-retryable. Caller can inspect detail.
        import llm
        if isinstance(e, llm.LLMError):
            status = 502 if e.retryable else 500
            raise HTTPException(status_code=status,
                                detail={"error": str(e), "retryable": e.retryable,
                                        "api_call_id": e.api_call_id})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/routing_events")
def routing_events(limit: int = 25) -> dict[str, Any]:
    """Recent router-log ingestion summary + last N renders inserted by
    the router tailer. Returns the most recent run's summary plus
    renders rows where discipline_version='1.0' (post-v1 baseline)."""
    payload: dict[str, Any] = {}
    try:
        import runtime
        payload["last_tail_summary"] = runtime.get_last_router_tail_summary()
    except Exception as e:
        payload["last_tail_summary"] = {"error": str(e)}
    try:
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, filepath, tool, hero_status, download_hash,
                       canonical_hash, discipline_version, created
                FROM renders
                WHERE discipline_version = '1.0'
                ORDER BY created DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            payload["recent_routed_renders"] = [
                {
                    "id": r[0], "filepath": r[1], "tool": r[2],
                    "hero_status": r[3],
                    "download_hash": (r[4][:16] + "...") if r[4] else None,
                    "canonical_hash": r[5][:16] + "...",
                    "discipline_version": r[6], "created": r[7],
                }
                for r in rows
            ]
    except (FileNotFoundError, sqlite3.Error) as e:
        payload["error"] = str(e)
    return payload
