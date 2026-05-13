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
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import assistant_tools
import audit
import audit_consult
import db
import dispatcher
import llm


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
    """New journey-oriented home. Sidebar shell + hero cards for
    'New video' / 'Continue EP1' / 'API keys'. Power-user shell moved to /tools."""
    return TEMPLATES.TemplateResponse("home.html", {"request": request, "active": None})


@app.get("/tools", response_class=HTMLResponse)
def tools_page(request: Request):
    """Power-user shell — concepts CRUD, draft prompts, recent prompts,
    awaiting/unbound/inbox queues, discipline drift. The pre-shell homepage."""
    return TEMPLATES.TemplateResponse("index.html", {"request": request, "active": "tools"})


@app.get("/video/new", response_class=HTMLResponse)
def video_new_page(request: Request):
    """Placeholder for 'start a new video' wizard. Greenfield creation
    isn't wired in v1; EP1 is the only project."""
    return TEMPLATES.TemplateResponse("video_new.html", {"request": request, "active": None})


@app.get("/video/{ep_id}", response_class=HTMLResponse)
def video_dashboard_page(request: Request, ep_id: str):
    """Episode dashboard — section progress + quick actions."""
    titles = {
        "ep1": ("EP1 — The Business of Addiction",
                "Behavioral psychology + attention economy. Launches 2026-05-16."),
    }
    ep_title, ep_subtitle = titles.get(
        ep_id, (ep_id.upper(), "Episode dashboard"))
    return TEMPLATES.TemplateResponse(
        "episode_dashboard.html",
        {"request": request, "active": ep_id, "ep_id": ep_id,
         "ep_title": ep_title, "ep_subtitle": ep_subtitle},
    )


@app.get("/video/{ep_id}/sections")
def video_sections_endpoint(ep_id: str) -> dict[str, Any]:
    """Section progress for an episode. v1 derives sections from filename
    patterns (concept→prompt→render linkage is sparse — most renders predate
    the concept system). Patterns matched: EP1_section_<N><L>_, ^H<N>_, ^K<N>_,
    ^section_<N><L>_."""
    import re
    payload: dict[str, Any] = {"ep_id": ep_id, "sections": [], "totals": {}}
    ep_token = ep_id.upper()  # filenames use EP1 not ep1
    # Patterns to extract section name from filename
    patterns = [
        re.compile(rf"^{ep_token}_section_(\d+[A-Z]?)_", re.IGNORECASE),
        re.compile(r"^section_(\d+[A-Z]?)_", re.IGNORECASE),
        re.compile(r"^(H\d+)[_.]", re.IGNORECASE),
        re.compile(r"^(K\d+)[_.]", re.IGNORECASE),
        re.compile(rf"^{ep_token}_(H\d+)[_.]", re.IGNORECASE),
        re.compile(rf"^{ep_token}_(K\d+)[_.]", re.IGNORECASE),
        re.compile(r"_(H\d+)_", re.IGNORECASE),
        re.compile(rf"^{ep_token}_(\d+[A-Z]?)_", re.IGNORECASE),
    ]

    def extract_section(filename: str) -> Optional[str]:
        if not filename:
            return None
        for pat in patterns:
            m = pat.search(filename)
            if m:
                tok = m.group(1)
                # Normalize: numeric sections as "§N", H/K as-is
                if tok[0].isdigit():
                    return f"§{tok}"
                return tok.upper()
        return None

    try:
        with db.connect() as conn:
            conn.row_factory = sqlite3.Row
            # Aggregate by section over all renders
            section_data: dict[str, dict[str, int]] = {}
            for row in conn.execute(
                "SELECT id, filename FROM renders"
            ):
                sec = extract_section(row["filename"] or "")
                if not sec:
                    continue
                d = section_data.setdefault(sec, {
                    "renders": 0, "verdicts": 0, "heroes": 0,
                })
                d["renders"] += 1
            # Verdicts per section
            for row in conn.execute(
                "SELECT r.filename FROM verdicts v "
                "JOIN renders r ON r.id = v.render_id"
            ):
                sec = extract_section(row["filename"] or "")
                if not sec or sec not in section_data:
                    continue
                section_data[sec]["verdicts"] += 1
            # Hero promotions per section
            for row in conn.execute(
                "SELECT r.filename FROM hero_promotions h "
                "JOIN renders r ON r.id = h.render_id"
            ):
                sec = extract_section(row["filename"] or "")
                if not sec or sec not in section_data:
                    continue
                section_data[sec]["heroes"] += 1

            sections = []
            totals = {"verdicts": 0, "renders": 0, "hero_locked": 0,
                      "audit_pending": 0}
            for sec, d in sorted(section_data.items(),
                                 key=lambda kv: (kv[0][0] != '§', kv[0])):
                if d["heroes"] > 0:
                    status = "hero_locked"
                elif d["verdicts"] > 0:
                    status = "verdict_stage"
                elif d["renders"] > 0:
                    status = "audit_pending"
                else:
                    status = "unstarted"
                sections.append({"section": sec, "status": status, "counts": d})
                totals["renders"] += d["renders"]
                totals["verdicts"] += d["verdicts"]
                if status == "hero_locked":
                    totals["hero_locked"] += 1
                if status == "audit_pending":
                    totals["audit_pending"] += 1
            payload["sections"] = sections
            payload["totals"] = totals
    except (FileNotFoundError, sqlite3.Error) as e:
        payload["error"] = str(e)
    return payload


class VideoChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class VideoChatRequest(BaseModel):
    message: str
    history: list[VideoChatMessage] = []


@app.post("/video/{ep_id}/chat")
def video_chat_endpoint(ep_id: str, body: VideoChatRequest) -> dict[str, Any]:
    """Project assistant chat for an episode. Builds project context
    (sections, recent activity) into system prompt; takes message history
    + new message, returns Claude response.

    Single-turn under the hood — history is concatenated into the user
    message rather than sent as separate messages list. Multi-turn
    structured chat is a future iteration.
    """
    # Pull fresh project context from sections endpoint logic
    sections_data = video_sections_endpoint(ep_id)
    sections = sections_data.get("sections", [])
    totals = sections_data.get("totals", {})

    # Recent activity for grounding
    last_verdict = None
    last_consult = None
    try:
        with db.connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT v.verdict, v.audited_by, v.created, r.filename "
                "FROM verdicts v LEFT JOIN renders r ON r.id=v.render_id "
                "ORDER BY v.created DESC LIMIT 1"
            ).fetchone()
            last_verdict = dict(row) if row else None
            row = conn.execute(
                "SELECT c.model, c.cost_usd, c.consulted_at, "
                "       v.verdict AS verdict_label, r.filename "
                "FROM ai_consultations c "
                "LEFT JOIN verdicts v ON v.id=c.verdict_id "
                "LEFT JOIN renders r ON r.id=v.render_id "
                "ORDER BY c.consulted_at DESC LIMIT 1"
            ).fetchone()
            last_consult = dict(row) if row else None
    except (FileNotFoundError, sqlite3.Error):
        pass

    # System prompt: project identity + state + behavioral rules
    from datetime import date
    launch = date(2026, 5, 16)
    today = date.today()
    days_left = (launch - today).days
    days_phrase = (
        f"in {days_left} days" if days_left > 0
        else "TODAY" if days_left == 0
        else f"{-days_left} days ago (LAUNCHED)"
    )
    system_lines = [
        f"You are the project assistant for a video production workspace. "
        f"The user (Joseph) is producing **EP1 — The Business of Addiction**, "
        f"an investigative-essay docudrama on behavioral psychology and the "
        f"attention economy, launching 2026-05-16 ({days_phrase}). "
        f"Today is {today.isoformat()}.",
        "",
        "**Your role:** help Joseph decide what to work on next, draft prompts, "
        "interpret audit results, and reason about production decisions. "
        "Be concrete and specific — name sections, name renders, name actions. "
        "Don't be sycophantic. Push back if his idea has a problem.",
        "",
        "**Current production state:**",
        f"- Sections detected: {len(sections)} ({totals.get('hero_locked', 0)} hero-locked, "
        f"{totals.get('audit_pending', 0)} audit-pending)",
        f"- Total renders in workspace: {totals.get('renders', 0)}",
        f"- Verdicts captured: {totals.get('verdicts', 0)}",
        "",
        "**Section breakdown:**",
    ]
    for s in sections:
        c = s["counts"]
        system_lines.append(
            f"- {s['section']}: {s['status']} "
            f"({c['renders']} renders, {c['verdicts']} verdicts, "
            f"{c.get('heroes', 0)} heroes)"
        )
    if last_verdict:
        system_lines += [
            "",
            f"**Most recent verdict:** {last_verdict['verdict']} on "
            f"`{(last_verdict.get('filename') or '')[:80]}` at "
            f"{last_verdict.get('created', '')[:19]} (by {last_verdict['audited_by']}).",
        ]
    if last_consult:
        system_lines += [
            f"**Most recent AI consult:** {last_consult.get('verdict_label')} verdict, "
            f"${last_consult.get('cost_usd', 0):.4f}, model={last_consult.get('model')}, "
            f"file `{(last_consult.get('filename') or '')[:80]}`.",
        ]
    system_lines += [
        "",
        "**You have file/shell/db tools** (read_file, list_directory, search_files, "
        "query_db, see_image, write_file, edit_file, run_bash). Use them freely to "
        "investigate before answering. AD-5: writes are AUTO-REFUSED for "
        "`projects/latent_systems/{shared,ep1,docs,tools}/` — those are Joseph's "
        "creative paths. You may write/edit anywhere else (especially "
        "`projects/latent_systems/tool_build/`). Bash refuses commands that mention "
        "canonical paths.",
        "",
        "**Available pages in this app:**",
        "- /  (home / project picker)",
        "- /video/ep1  (this dashboard)",
        "- /video/ep1/section/<NAME>  (per-section asset workspace with thumbnails)",
        "- /audit/grid  (audit grid; supports ?section=&only_unverdicted=true)",
        "- /audit/inbox  (process pending downloads)",
        "- /tools  (power-user shell — concepts CRUD, draft prompts, etc.)",
        "- /settings/keys  (API key status)",
        "",
        "When recommending action, name the section and link the URL. When changing "
        "code, read first, edit precisely, restart the server if needed, run tests "
        "if you touched backend code (`for f in projects/latent_systems/tool_build/"
        "tests/test_*.py; do python \"$f\"; done`).",
    ]
    system_prompt = "\n".join(system_lines)

    history_dicts = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        import assistant_runner
        result = assistant_runner.run_assistant(
            system=system_prompt,
            user_message=body.message,
            history=history_dicts,
        )
    except llm.LLMError as e:
        status = 502 if e.retryable else 500
        raise HTTPException(
            status_code=status,
            detail={"error": str(e), "retryable": e.retryable,
                    "api_call_id": e.api_call_id},
        )
    return result


def _section_filename_match(filename: str, ep_id: str, section: str) -> bool:
    """Does this filename look like it belongs to this section? Mirrors the
    extraction logic used in /video/{ep_id}/sections."""
    import re
    if not filename:
        return False
    ep_token = ep_id.upper()
    # Strip § prefix for matching
    sec_match = section.lstrip("§")
    pats = [
        rf"^{ep_token}_section_{re.escape(sec_match)}_",
        rf"^section_{re.escape(sec_match)}_",
        rf"^{re.escape(sec_match)}[_.]",
        rf"^{ep_token}_{re.escape(sec_match)}[_.]",
        rf"_{re.escape(sec_match)}_",
    ]
    fl = filename
    for p in pats:
        if re.search(p, fl, re.IGNORECASE):
            return True
    return False


@app.get("/video/{ep_id}/section/{section}", response_class=HTMLResponse)
def video_section_workspace_page(request: Request, ep_id: str, section: str):
    """Section workspace page — renders, audio players, verdicts, actions
    scoped to one section of the episode."""
    return TEMPLATES.TemplateResponse(
        "section_workspace.html",
        {"request": request, "active": ep_id, "ep_id": ep_id,
         "section": section},
    )


@app.get("/video/{ep_id}/section/{section}/data")
def video_section_data_endpoint(ep_id: str, section: str) -> dict[str, Any]:
    """Renders + verdicts + counts for one section, identified by filename
    pattern matching."""
    payload: dict[str, Any] = {
        "ep_id": ep_id, "section": section,
        "renders": [], "verdicts": [], "counts": {},
    }
    try:
        with db.connect() as conn:
            conn.row_factory = sqlite3.Row
            # Renders for this section
            renders = []
            for row in conn.execute(
                "SELECT id, filename, filepath, tool, hero_status, created "
                "FROM renders ORDER BY created DESC"
            ):
                if _section_filename_match(row["filename"] or "", ep_id, section):
                    renders.append(dict(row))
            payload["renders"] = renders

            # Verdicts on those renders
            render_ids = [r["id"] for r in renders]
            if render_ids:
                placeholders = ",".join("?" * len(render_ids))
                verdicts = conn.execute(
                    f"SELECT v.id, v.render_id, v.verdict, v.audited_by, "
                    f"       v.created, r.filename "
                    f"FROM verdicts v JOIN renders r ON r.id=v.render_id "
                    f"WHERE v.render_id IN ({placeholders}) "
                    f"ORDER BY v.created DESC",
                    render_ids,
                ).fetchall()
                payload["verdicts"] = [dict(v) for v in verdicts]
                # Counts
                payload["counts"] = {
                    "renders": len(renders),
                    "verdicts": len(verdicts),
                    "verdicted_render_ids": list(set(
                        v["render_id"] for v in verdicts
                    )),
                }
            else:
                payload["counts"] = {"renders": 0, "verdicts": 0,
                                     "verdicted_render_ids": []}
    except (FileNotFoundError, sqlite3.Error) as e:
        payload["error"] = str(e)
    return payload


@app.get("/settings/keys", response_class=HTMLResponse)
def settings_keys_page(request: Request):
    """API keys + integrations management."""
    return TEMPLATES.TemplateResponse(
        "settings_keys.html", {"request": request, "active": "keys"})


@app.get("/settings/keys/status")
def settings_keys_status() -> dict[str, Any]:
    """Status of known + future integrations. v1 read-only — surfaces
    which env vars are set, what each unlocks. Add/edit via UI is deferred."""
    import os
    known = [
        {
            "label": "Anthropic (Claude)",
            "env_var": "ANTHROPIC_API_KEY",
            "configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "used_for": "Prompt drafting (/prompts/draft_via_api), AI vision audit consultation (/audit/render/.../consult)",
        },
    ]
    future = [
        {"label": "ElevenLabs", "env_var": "ELEVENLABS_API_KEY",
         "unlocks": "TTS for narration takes (currently done in ElevenLabs web UI manually)"},
        {"label": "OpenAI", "env_var": "OPENAI_API_KEY",
         "unlocks": "GPT Image 2 generation, ChatGPT-side scripting passes"},
        {"label": "Midjourney", "env_var": "MIDJOURNEY_API_KEY",
         "unlocks": "Direct MJ generation (currently clipboard-handoff workflow)"},
        {"label": "fal.ai", "env_var": "FAL_KEY",
         "unlocks": "FLUX, Seedance, Kling video generation via fal gateway"},
        {"label": "Replicate", "env_var": "REPLICATE_API_TOKEN",
         "unlocks": "Open-source model hosting (FLUX, Stable Diffusion, etc.)"},
    ]
    return {"known": known, "future": future}


@app.get("/audit", response_class=HTMLResponse)
def audit_view(
    request: Request,
    session_id: Optional[str] = None,
    render_id: Optional[str] = None,
    only_unverdicted: bool = False,
    tool: Optional[str] = None,
    section: Optional[str] = None,
    flagged_only: bool = False,
):
    """Audit viewer page (Wave A). Serial view of one render at a time;
    keyboard 1-4 captures verdict, F toggles flag, ←/→ navigates queue.

    Query params drive the queue filter; session_id is optional (if
    omitted, verdict capture writes without session attribution).
    render_id selects which render to display; defaults to first in
    filtered queue.
    """
    # Pull queue (cap at reasonable limit for nav-by-index)
    queue = audit.list_audit_queue(
        only_unverdicted=only_unverdicted, tool_filter=tool,
        section_filter=section, flagged_only=flagged_only,
        limit=500,  # large enough to not need pagination for audit run
    )
    items = queue["items"]
    if not items:
        return TEMPLATES.TemplateResponse(
            "audit.html",
            {"request": request, "render": None, "queue_total": 0,
             "session_id": session_id, "session": None,
             "filters": {"only_unverdicted": only_unverdicted, "tool": tool,
                         "section": section, "flagged_only": flagged_only}},
        )

    # Locate current render in queue (default to first)
    if render_id is None:
        render_id = items[0]["render_id"]
    try:
        idx = next(
            i for i, it in enumerate(items) if it["render_id"] == render_id
        )
    except StopIteration:
        # render_id not in filtered queue — render it but no nav
        idx = -1

    detail = audit.get_render_detail(render_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"render {render_id} not found")

    prev_render_id = items[idx - 1]["render_id"] if idx > 0 else None
    next_render_id = (
        items[idx + 1]["render_id"]
        if 0 <= idx < len(items) - 1 else None
    )

    session = audit.get_audit_session(session_id) if session_id else None

    return TEMPLATES.TemplateResponse(
        "audit.html",
        {
            "request": request,
            "render": detail,
            "session_id": session_id,
            "session": session,
            "queue_total": queue["total"],
            "queue_position": (idx + 1) if idx >= 0 else None,
            "prev_render_id": prev_render_id,
            "next_render_id": next_render_id,
            "filters": {
                "only_unverdicted": only_unverdicted, "tool": tool,
                "section": section, "flagged_only": flagged_only,
            },
        },
    )


@app.get("/audit/grid", response_class=HTMLResponse)
def audit_grid_view(
    request: Request,
    session_id: Optional[str] = None,
    only_unverdicted: bool = False,
    tool: Optional[str] = None,
    section: Optional[str] = None,
    media_type: Optional[str] = None,
    flagged_only: bool = False,
    sort_by: str = "created",
    page: int = 1,
    per_page: int = 20,
):
    """Grid view. Filters compose with audit.list_audit_queue;
    pagination via page (1-indexed) + per_page.

    media_type: 'image' / 'video' / 'audio' (filename-extension based).
    sort_by: 'created' (default) or 'rank' (Claude pre-rank score DESC).
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 200:
        per_page = 20
    offset = (page - 1) * per_page
    queue = audit.list_audit_queue(
        only_unverdicted=only_unverdicted, tool_filter=tool,
        section_filter=section, media_type_filter=media_type,
        flagged_only=flagged_only, sort_by=sort_by,
        limit=per_page, offset=offset,
    )

    # Per-thumbnail verdict (latest non-superseded) for the badge overlay.
    # Single query batched over all rendered IDs for efficiency.
    items = queue["items"]
    verdicts_by_render: dict[str, dict] = {}
    if items:
        render_ids = [it["render_id"] for it in items]
        placeholders = ",".join("?" for _ in render_ids)
        with db.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT v.render_id, v.verdict, v.flags_needs_second_look
                FROM verdicts v
                WHERE v.render_id IN ({placeholders})
                  AND v.id NOT IN (
                    SELECT supersedes_verdict_id FROM verdicts
                    WHERE supersedes_verdict_id IS NOT NULL
                  )
                ORDER BY v.created DESC
                """,
                render_ids,
            ).fetchall()
        # Earliest in result set wins (we ORDER BY created DESC; first
        # row per render_id is the most recent non-superseded verdict).
        for r in rows:
            if r[0] not in verdicts_by_render:
                verdicts_by_render[r[0]] = {
                    "verdict": r[1],
                    "flags_needs_second_look": bool(r[2]),
                }

    session = audit.get_audit_session(session_id) if session_id else None
    total = queue["total"]
    last_page = max(1, (total + per_page - 1) // per_page)

    return TEMPLATES.TemplateResponse(
        "audit_grid.html",
        {
            "request": request,
            "items": items,
            "verdicts_by_render": verdicts_by_render,
            "session_id": session_id,
            "session": session,
            "queue_total": total,
            "page": page,
            "per_page": per_page,
            "last_page": last_page,
            "filters": {
                "only_unverdicted": only_unverdicted, "tool": tool,
                "section": section, "flagged_only": flagged_only,
                "media_type": media_type, "sort_by": sort_by,
            },
        },
    )


class RankBatchRequest(BaseModel):
    section: Optional[str] = None
    media_type: Optional[str] = None
    only_unverdicted: bool = True
    only_unranked: bool = True
    max_renders: int = 60
    batch_size: int = 6


@app.post("/audit/rank-batch")
def audit_rank_batch_endpoint(body: RankBatchRequest) -> dict[str, Any]:
    """Score renders with Claude vision (1-10) and persist to assistant_ranks.

    Picks renders matching filters, batches them through claude-opus-4-7,
    parses scores, writes assistant_ranks rows. Reloads of the audit grid
    sorted by rank surface the highest-scored renders first.
    """
    import json as _json
    import re
    import anthropic
    from datetime import datetime, timezone

    # Pull candidate renders
    queue = audit.list_audit_queue(
        only_unverdicted=body.only_unverdicted,
        section_filter=body.section,
        media_type_filter=body.media_type or "image",  # only images for v1
        limit=body.max_renders, offset=0,
    )
    candidates = queue["items"]
    if body.only_unranked:
        candidates = [c for c in candidates if c.get("rank_score") is None]
    if not candidates:
        return {"ranked": 0, "batches": 0, "cost_usd": 0,
                "skipped_reason": "no candidates match (already ranked or empty)"}

    client = anthropic.Anthropic()
    total_cost = 0.0
    ranked = 0
    batches = 0
    errors: list[str] = []

    section_label = body.section or "(no section)"
    system = (
        "You evaluate AI-generated production renders for a docudrama project "
        "(EP1: behavioral psychology + attention economy) on a 1-10 hero-strength "
        "scale. 10 = lock as hero, 8-9 = strong contender, 5-7 = usable but not "
        "leading, 1-4 = reject. Be calibrated, not generous — most renders should "
        "land 3-6. For each image, return a JSON object with fields {render_id, "
        "score, summary} where summary is a single-sentence rationale. "
        f"Current section context: {section_label}."
    )

    # Process in batches
    for i in range(0, len(candidates), body.batch_size):
        chunk = candidates[i:i + body.batch_size]
        batches += 1
        # Build vision messages content
        content_blocks: list[dict] = [{
            "type": "text",
            "text": (
                f"Score these {len(chunk)} renders. Return a JSON array; one "
                "object per render in the same order as the images, each:\n"
                "{\"render_id\": \"...\", \"score\": <1-10>, \"summary\": \"...\"}\n"
                "Render IDs (in order):\n"
                + "\n".join(f"- {c['render_id']}  ({c['filename'][:80]})" for c in chunk)
            ),
        }]
        skipped: list[str] = []
        for c in chunk:
            try:
                img_block, _ = assistant_tools.execute_tool(
                    "see_image", {"render_id": c["render_id"]})
                if isinstance(img_block, dict) and img_block.get("type") == "image":
                    content_blocks.append(img_block)
                else:
                    skipped.append(c["render_id"])
            except Exception as e:
                skipped.append(c["render_id"])
                errors.append(f"{c['render_id']}: {e}")
        if len(content_blocks) <= 1:
            continue  # nothing usable in this batch

        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": content_blocks}],
            )
        except anthropic.APIError as e:
            errors.append(f"batch {batches}: {e}")
            continue

        usage = response.usage
        total_cost += llm.compute_cost(
            response.model,
            tokens_input=usage.input_tokens,
            tokens_output=usage.output_tokens,
            cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )

        # Extract JSON array from response text
        text = "".join(b.text for b in response.content if b.type == "text")
        # Strip markdown code fences if present
        match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
        if not match:
            errors.append(f"batch {batches}: no JSON array found in response")
            continue
        try:
            scores = _json.loads(match.group(0))
        except Exception as e:
            errors.append(f"batch {batches}: JSON parse failed: {e}")
            continue

        # Persist
        now = datetime.now(timezone.utc).isoformat()
        with db.connect() as conn:
            audit._ensure_assistant_ranks_table(conn)
            for s in scores:
                rid = s.get("render_id")
                score = s.get("score")
                summary = s.get("summary", "")
                if not rid or score is None:
                    continue
                try:
                    score_f = float(score)
                except (TypeError, ValueError):
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO assistant_ranks "
                    "(render_id, score, summary, model, ranked_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (rid, score_f, summary, response.model, now),
                )
                ranked += 1
            conn.commit()

    return {
        "ranked": ranked,
        "batches": batches,
        "candidates": len(candidates),
        "cost_usd": round(total_cost, 6),
        "errors": errors[:10],
    }


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


@app.get("/homepage_stats")
def homepage_stats_endpoint() -> dict[str, Any]:
    """At-a-glance counts + recent audit activity for the homepage.
    One round-trip vs spreading these across /api_status, /audit/queue,
    /verdicts, etc. Cheap COUNT(*) queries against indexed columns."""
    payload: dict[str, Any] = {}
    try:
        with db.connect() as conn:
            conn.row_factory = sqlite3.Row

            payload["stats"] = {
                "verdicts_total": conn.execute(
                    "SELECT COUNT(*) FROM verdicts"
                ).fetchone()[0],
                "consults_total": conn.execute(
                    "SELECT COUNT(*) FROM ai_consultations"
                ).fetchone()[0],
                "consults_completed": conn.execute(
                    "SELECT COUNT(*) FROM ai_consultations WHERE status='completed'"
                ).fetchone()[0],
                "renders_total": conn.execute(
                    "SELECT COUNT(*) FROM renders"
                ).fetchone()[0],
                "renders_unverdicted": conn.execute(
                    "SELECT COUNT(*) FROM renders r "
                    "LEFT JOIN verdicts v ON v.render_id=r.id "
                    "WHERE v.id IS NULL"
                ).fetchone()[0],
                "renders_pre_v1_hero": conn.execute(
                    "SELECT COUNT(*) FROM renders WHERE hero_status='pre_v1_hero'"
                ).fetchone()[0],
                "concepts_active": conn.execute(
                    "SELECT COUNT(*) FROM concepts WHERE status != 'archived'"
                ).fetchone()[0],
                "prompts_total": conn.execute(
                    "SELECT COUNT(*) FROM prompts"
                ).fetchone()[0],
                "prompts_draft": conn.execute(
                    "SELECT COUNT(*) FROM prompts WHERE status='draft'"
                ).fetchone()[0],
                "prompts_awaiting_return": conn.execute(
                    "SELECT COUNT(*) FROM prompts WHERE status='awaiting_return'"
                ).fetchone()[0],
                "attempts_in_flight": conn.execute(
                    "SELECT COUNT(*) FROM generation_attempts WHERE status='in_flight'"
                ).fetchone()[0],
            }

            row = conn.execute(
                "SELECT v.id, v.render_id, v.verdict, v.audited_by, v.created, "
                "       r.filename, r.tool "
                "FROM verdicts v "
                "LEFT JOIN renders r ON r.id = v.render_id "
                "ORDER BY v.created DESC LIMIT 1"
            ).fetchone()
            payload["last_verdict"] = dict(row) if row else None

            row = conn.execute(
                "SELECT c.id, c.verdict_id, c.model, c.status, c.cost_usd, "
                "       c.consulted_at, v.render_id, v.verdict AS verdict_label, "
                "       r.filename "
                "FROM ai_consultations c "
                "LEFT JOIN verdicts v ON v.id = c.verdict_id "
                "LEFT JOIN renders r ON r.id = v.render_id "
                "ORDER BY c.consulted_at DESC LIMIT 1"
            ).fetchone()
            payload["last_consult"] = dict(row) if row else None

            rows = conn.execute(
                "SELECT c.id, c.model, c.status, c.cost_usd, c.consulted_at, "
                "       v.verdict AS verdict_label, r.filename "
                "FROM ai_consultations c "
                "LEFT JOIN verdicts v ON v.id = c.verdict_id "
                "LEFT JOIN renders r ON r.id = v.render_id "
                "ORDER BY c.consulted_at DESC LIMIT 3"
            ).fetchall()
            payload["recent_consults"] = [dict(r) for r in rows]
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


# --- Phase 2 Wave A — Feature 4: audit viewer (non-AI mode) ---


class AuditSessionCreate(BaseModel):
    rubric_version: str = "1.0"
    mode: str = "quick_pass"
    scope_concept_id: Optional[str] = None
    scope_section: Optional[str] = None
    scope_filter: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class VerdictCreate(BaseModel):
    verdict: str
    verdict_reasoning: Optional[str] = None
    audited_by: str = "human"
    audit_session_id: Optional[str] = None
    rubric_version: Optional[str] = None
    rubric_used: Optional[str] = None
    rubric_criteria_match: Optional[dict[str, Any]] = None
    flags_needs_second_look: bool = False
    supersedes_verdict_id: Optional[str] = None


class VerdictFlagsUpdate(BaseModel):
    needs_second_look: Optional[bool] = None


@app.post("/audit/sessions", status_code=201)
def create_audit_session_endpoint(body: AuditSessionCreate) -> dict[str, Any]:
    """Start a new audit session (Wave A). Returns session record."""
    try:
        return audit.create_audit_session(
            rubric_version=body.rubric_version, mode=body.mode,
            scope_concept_id=body.scope_concept_id,
            scope_section=body.scope_section,
            scope_filter=body.scope_filter, notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/audit/sessions")
def list_audit_sessions_endpoint(
    limit: int = 50, active_only: bool = False,
) -> dict[str, Any]:
    """List audit sessions (newest first). active_only filters to ended IS NULL."""
    return {"sessions": audit.list_audit_sessions(limit=limit, active_only=active_only)}


@app.get("/audit/sessions/{session_id}")
def get_audit_session_endpoint(session_id: str) -> dict[str, Any]:
    record = audit.get_audit_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"audit_session {session_id} not found")
    return record


@app.post("/audit/sessions/{session_id}/end")
def end_audit_session_endpoint(session_id: str) -> dict[str, Any]:
    """Mark a session as ended. Idempotent."""
    try:
        return audit.end_audit_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/audit/render/{render_id}")
def audit_render_detail_endpoint(render_id: str) -> dict[str, Any]:
    """Render detail for audit viewer: image metadata + concept + lineage
    + latest non-superseded verdict."""
    record = audit.get_render_detail(render_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"render {render_id} not found")
    return record


@app.post("/audit/render/{render_id}/verdict", status_code=201)
def capture_verdict_endpoint(render_id: str, body: VerdictCreate) -> dict[str, Any]:
    """Instant filesystem write per F8 (no save button). YAML before SQL."""
    try:
        return audit.capture_verdict(
            render_id=render_id, verdict=body.verdict,
            verdict_reasoning=body.verdict_reasoning,
            audited_by=body.audited_by,
            audit_session_id=body.audit_session_id,
            rubric_version=body.rubric_version,
            rubric_used=body.rubric_used,
            rubric_criteria_match=body.rubric_criteria_match,
            flags_needs_second_look=body.flags_needs_second_look,
            supersedes_verdict_id=body.supersedes_verdict_id,
        )
    except ValueError as e:
        # 400 for invalid value (verdict type, audited_by); 404 for
        # missing references. Distinguish by message-prefix sniff —
        # cleaner alternative is to raise a typed exception, but
        # ValueError discipline matches the rest of the codebase.
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@app.patch("/audit/verdicts/{verdict_id}/flags")
def update_verdict_flags_endpoint(
    verdict_id: str, body: VerdictFlagsUpdate,
) -> dict[str, Any]:
    """Toggle verdict flags (currently needs_second_look only per Q3 minimal scope)."""
    try:
        return audit.update_verdict_flags(
            verdict_id, needs_second_look=body.needs_second_look,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


# --- F5 hero promotion atomic action (per F5_MODAL_UX_DRAFT.md v1.2) ---


class HeroPromoteRequest(BaseModel):
    audit_session_id: Optional[str] = None


class HeroUnPromoteRequest(BaseModel):
    reason: str
    audit_session_id: Optional[str] = None


@app.post("/audit/render/{render_id}/promote", status_code=201)
def hero_promote_endpoint(
    render_id: str, body: Optional[HeroPromoteRequest] = None,
) -> dict[str, Any]:
    """Atomic file-COPY + hero_promotions row insert; F6 prompt fires
    post-commit best-effort. Pre-validation surfaces caller-correctable
    errors as 400; missing render is 404; downstream atomic-transaction
    failures as 500 with rollback state in the message.
    """
    try:
        return dispatcher.hero_promote(
            render_id=render_id,
            audit_session_id=body.audit_session_id if body else None,
        )
    except dispatcher.HeroPromotionError as e:
        msg = str(e)
        # 404 for missing render; 409 for already-promoted (the only
        # conflict state); 400 for ineligible verdict / no section /
        # other pre-validation; 500 for atomic-transaction failures.
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        if "already promoted" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "transaction failed" in msg or "rollback failed" in msg:
            raise HTTPException(status_code=500, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@app.post("/audit/render/{render_id}/un_promote", status_code=201)
def hero_un_promote_endpoint(
    render_id: str, body: HeroUnPromoteRequest,
) -> dict[str, Any]:
    """Atomic file-MOVE (winners/ → _DEPRECATED_<reason>/) + DB update.
    Reason is required (>= 5 chars per channel staple #12); sanitization
    happens server-side. F6 prompt fires post-commit best-effort.
    """
    try:
        return dispatcher.hero_un_promote(
            render_id=render_id,
            reason=body.reason,
            audit_session_id=body.audit_session_id,
        )
    except dispatcher.HeroPromotionError as e:
        msg = str(e)
        if "no active promotion" in msg or "missing at" in msg:
            raise HTTPException(status_code=404, detail=msg)
        if "destination already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "transaction failed" in msg or "rollback failed" in msg:
            raise HTTPException(status_code=500, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@app.get("/audit/queue")
def audit_queue_endpoint(
    only_unverdicted: bool = False, tool: Optional[str] = None,
    section: Optional[str] = None, flagged_only: bool = False,
    needs_review_paths: bool = False,
    limit: int = 50, offset: int = 0,
) -> dict[str, Any]:
    """Audit queue with composable filters. Default order: newest first."""
    return audit.list_audit_queue(
        only_unverdicted=only_unverdicted, tool_filter=tool,
        section_filter=section, flagged_only=flagged_only,
        needs_review_paths=needs_review_paths,
        limit=limit, offset=offset,
    )


@app.get("/audit/cost")
def audit_cost_endpoint(session_id: str) -> dict[str, Any]:
    """Cost rollup for a session. Wave A: $0 baseline (no AI consultations).
    Wave B layers ai_consultations.cost_usd into total_cost_usd."""
    record = audit.get_session_cost(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"audit_session {session_id} not found")
    return record


@app.get("/audit/thumbnail/{render_id}")
def audit_thumbnail_endpoint(render_id: str):
    """Serve thumbnail with hash-stable invalidation per design notes §5.
    Cache hit: source_hash == renders.canonical_hash AND file exists.
    Cache miss / stale: generate new thumbnail (max edge 1568px JPEG).
    Returns 404 if render not in db OR file missing OR processing failed."""
    import thumbnails
    info = thumbnails.get_or_generate(render_id)
    if info is None:
        raise HTTPException(
            status_code=404,
            detail=f"render {render_id} not found, file missing, or unprocessable",
        )
    return FileResponse(str(info["thumbnail_abs_path"]), media_type="image/jpeg")


@app.get("/audit/render/{render_id}/file")
def audit_render_file_endpoint(render_id: str):
    """Serve the full original render file (for serial-view fullsize
    display). No downscaling — Joseph audits at native resolution.
    For grid view's smaller previews, use /audit/thumbnail/{render_id}."""
    import thumbnails
    abs_path = thumbnails.get_render_abs_path(render_id)
    if abs_path is None:
        raise HTTPException(
            status_code=404, detail=f"render {render_id} not found or file missing",
        )
    return FileResponse(str(abs_path))


# --- Phase 2 Wave B — Feature 4 sub-feature: AI consultation ---


class ConsultRequest(BaseModel):
    audit_session_id: Optional[str] = None
    providers: list[str] = ["anthropic"]
    create_verdict_if_missing: bool = False


@app.post("/audit/render/{render_id}/consult", status_code=201)
def consult_render_endpoint(
    render_id: str, body: ConsultRequest,
) -> dict[str, Any]:
    """Run AI consultation against a render against the active rubric.
    Persists ai_consultations rows + YAMLs. Wave B.

    create_verdict_if_missing (v0.6 amendment 1): default False refuses
    to auto-create a placeholder verdict when none exists — caller must
    mark a verdict first (preserving F8 verdict-as-commitment) or
    explicitly opt in. Set True to restore the legacy auto-create path.

    Errors:
      400 — no rubric authored / image unprocessable / unknown provider /
            no verdict exists and create_verdict_if_missing is False.
      404 — render not found.
      500 / 502 — SDK failure (502 retryable, 500 permanent), payload
                  includes api_call_id for retry-queue correlation.
    """
    try:
        return audit_consult.consult_render(
            render_id, audit_session_id=body.audit_session_id,
            providers=body.providers,
            create_verdict_if_missing=body.create_verdict_if_missing,
        )
    except audit_consult.ConsultationError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except llm.LLMError as e:
        # Same handling shape as draft_via_api: 502 for retryable
        # (rate limit, timeout, network); 500 for permanent (auth,
        # bad request) so the UI can route to retry queue or modal.
        status = 502 if e.retryable else 500
        raise HTTPException(
            status_code=status,
            detail={
                "error": str(e), "retryable": e.retryable,
                "api_call_id": e.api_call_id,
            },
        )


# --- Phase 2.5 — pending-downloads inbox (web-UI ingestion gap fix) ---


class IngestRequest(BaseModel):
    source_path: str
    destination_dir: str


@app.get("/audit/inbox", response_class=HTMLResponse)
def audit_inbox_page(request: Request, session_id: Optional[str] = None):
    """Inbox page surfacing pending Downloads as ingestable cards.

    Closes the workflow gap where MJ/Kling web-UI generations land in
    Downloads, get hashed by the watcher, but never become `renders`
    rows because they have no in-flight prompt attempt to bind to.
    Joseph picks a destination per-file; ingest copies + walks.
    """
    import inbox
    items = inbox.list_pending()
    session = audit.get_audit_session(session_id) if session_id else None
    return TEMPLATES.TemplateResponse(
        "audit_inbox.html",
        {
            "request": request,
            "items": items,
            "session_id": session_id,
            "session": session,
        },
    )


@app.get("/audit/inbox/api/list")
def audit_inbox_list_endpoint() -> dict[str, Any]:
    """JSON list of pending downloads with filename heuristics-based
    destination suggestions. Used by the inbox page (server-side render)
    and any future polling/refresh affordance."""
    import inbox
    return {"items": inbox.list_pending()}


@app.post("/audit/inbox/api/ingest", status_code=201)
def audit_inbox_ingest_endpoint(body: IngestRequest) -> dict[str, Any]:
    """Copy a pending Downloads file to a canonical path + run walker so
    the new file becomes an audit-grid-visible `renders` row.

    Errors:
      400 — destination outside latent_systems/ (AD-5 guard) or not a directory
      404 — source file or destination directory not found
      409 — file with same name already exists at destination
    """
    import inbox
    result = inbox.ingest_file(
        source_path=body.source_path,
        destination_dir=body.destination_dir,
    )
    if not result.get("ok"):
        err = result.get("error", "")
        if err in ("source_not_found", "dest_not_found"):
            raise HTTPException(status_code=404, detail=result["message"])
        if err == "dest_exists":
            raise HTTPException(status_code=409, detail=result["message"])
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/audit/inbox/thumbnail")
def audit_inbox_thumbnail_endpoint(path: str):
    """Serve a pending Downloads image for thumbnail rendering in the
    inbox page. Security: only serves paths the watcher currently tracks
    (prevents arbitrary filesystem read via this endpoint)."""
    import inbox
    from pathlib import Path
    p = Path(path)
    pending_paths = {item["path"] for item in inbox.list_pending()}
    if str(p) not in pending_paths:
        raise HTTPException(status_code=403,
                            detail="path not in pending_downloads")
    if not p.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(str(p))
