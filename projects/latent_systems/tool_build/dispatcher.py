"""Clipboard handoff dispatcher (Feature 3b mechanic, Day 7).

Translates a draft prompt into the "expecting return for prompt X" state:
  1. Write prompt text to OS clipboard via pyperclip.
  2. Open the target tool's web UI in the browser.
  3. Insert a generation_attempts row (status=in_flight).
  4. Update prompt status to 'awaiting_return'.

Day 7 implements the mechanic. Day 8 layers failure-mode timers
(3b.1-3b.8) on top. Day 9 handles return-binding when render files
flow in via the router_tail.

Tool URLs are config-driven. Override via TOOL_URLS at the call site
or extend the dict if/when other clipboard-handoff tools land.
"""

from __future__ import annotations

import sqlite3
import webbrowser
from datetime import datetime, timezone
from typing import Optional

import pyperclip

import db
from constants import CURRENT_DISCIPLINE_VERSION


TOOL_URLS = {
    "midjourney": "https://www.midjourney.com/imagine",
    "kling": "https://app.klingai.com/global/",
    # Future clipboard-handoff tools added here.
}

# Aging thresholds for derived attempt status (Day 8 — Section 1 / 3b.1).
# Computed at query time from attempt.started, no background task needed.
AGE_STILL_WAITING_S = 30 * 60        # 30 min  -> "still_waiting"
AGE_STALE_CHECK_S = 24 * 3600        # 24 h    -> "stale_check"

# Inbox path fragments — router routes low-confidence files into these
# subdirs (per router_config.yaml destinations). Used by inbox_renders().
INBOX_PATH_FRAGMENTS = (
    "/visual_identity_phase1_references/_inbox/",
    "/visual_identity_phase1_references/_unclassified/",
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_attempt_number(conn: sqlite3.Connection, prompt_id: str) -> int:
    """Return next attempt_number for a prompt (1-indexed)."""
    row = conn.execute(
        "SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM generation_attempts WHERE prompt_id = ?",
        (prompt_id,),
    ).fetchone()
    return int(row[0])


# Schema 0002 added started_orig (immutable original dispatch timestamp).
# kick_attempt mutates started but NEVER started_orig, so audit queries
# can ask "how long was this attempt actually outstanding?" via
# (completed - started_orig) instead of (completed - kicked-started).
# A trigger on generation_attempts auto-populates started_orig from
# started when it's NULL on INSERT (defense-in-depth for forgotten code
# paths or test fixtures), but production code should set it explicitly.


def _open_browser(url: str) -> bool:
    """Open URL in the default browser. Returns True if webbrowser
    accepted the request (which doesn't guarantee the browser actually
    opened — webbrowser is best-effort)."""
    try:
        return webbrowser.open(url, new=2)  # new=2 → new tab if possible
    except Exception:
        return False


def dispatch(
    *, prompt_id: str, prompt_text: str, tool: str,
    notes: Optional[str] = None,
    open_url: bool = True,
    write_clipboard: bool = True,
) -> dict:
    """Execute the dispatch mechanic. Returns summary dict.

    open_url and write_clipboard are flags so tests can run without
    side-effecting the user's actual browser/clipboard.
    """
    if tool not in TOOL_URLS:
        raise ValueError(f"unknown tool '{tool}' — add to dispatcher.TOOL_URLS")

    summary = {
        "prompt_id": prompt_id,
        "tool": tool,
        "url": TOOL_URLS[tool],
        "clipboard_written": False,
        "browser_opened": False,
        "attempt_id": None,
        "attempt_number": None,
        "errors": [],
    }

    # 1. Clipboard write (if enabled).
    if write_clipboard:
        try:
            pyperclip.copy(prompt_text)
            summary["clipboard_written"] = True
        except pyperclip.PyperclipException as e:
            summary["errors"].append(f"clipboard write failed: {e}")

    # 2. Generation_attempts row + prompt status update (atomic).
    conn = db.connect()
    try:
        with conn:  # implicit transaction
            attempt_number = _next_attempt_number(conn, prompt_id)
            attempt_id = f"att_{prompt_id}_{attempt_number}"
            now = _iso_now()
            # started_orig = started at insert time (immutable per §4.7);
            # kick_attempt later updates only `started`, leaving started_orig
            # as the audit anchor for true elapsed time.
            conn.execute(
                """
                INSERT INTO generation_attempts (
                    id, prompt_id, attempt_number, started, started_orig,
                    completed, status, trigger_method, notes
                ) VALUES (?, ?, ?, ?, ?, NULL, 'in_flight', 'clipboard_handoff', ?)
                """,
                (attempt_id, prompt_id, attempt_number, now, now, notes),
            )
            conn.execute(
                "UPDATE prompts SET status = 'awaiting_return' WHERE id = ?",
                (prompt_id,),
            )
        summary["attempt_id"] = attempt_id
        summary["attempt_number"] = attempt_number
    except sqlite3.Error as e:
        summary["errors"].append(f"db write failed: {e}")
    finally:
        conn.close()

    # 3. Open browser (after DB commit so we don't open browser only to
    # fail to record state).
    if open_url and not summary["errors"]:
        summary["browser_opened"] = _open_browser(TOOL_URLS[tool])

    return summary


def list_prompts(*, limit: int = 50) -> list[dict]:
    """Return recent prompts ordered by creation desc. For UI listing."""
    conn = db.connect()
    try:
        rows = conn.execute(
            """
            SELECT p.id, p.concept_id, p.tool, p.text_preview, p.status,
                   p.discipline_version, p.created,
                   (SELECT COUNT(*) FROM generation_attempts ga WHERE ga.prompt_id = p.id)
                   AS attempts
            FROM prompts p
            ORDER BY p.created DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0], "concept_id": r[1], "tool": r[2],
                "text_preview": r[3], "status": r[4],
                "discipline_version": r[5], "created": r[6],
                "attempts": r[7],
            }
            for r in rows
        ]
    finally:
        conn.close()


def create_prompt(
    *, prompt_text: str, tool: str = "midjourney",
    concept_id: Optional[str] = None,
    drafted_by: str = "manual",
    discipline_version: str = CURRENT_DISCIPLINE_VERSION,
    concept_text: Optional[str] = None,
) -> dict:
    """Insert a draft prompt. Returns the new prompt record.

    `concept_text` is the originating concept (for API drafting) — stored in
    the YAML so retry paths can reconstruct the API call without an external
    queue payload. None for manually-typed prompts.
    """
    import hashlib
    now = _iso_now()
    # Stable ID derived from text content + creation time so re-creates
    # don't collide.
    prompt_id = hashlib.sha256(
        f"{prompt_text}|{now}".encode("utf-8")
    ).hexdigest()[:16]
    text_preview = prompt_text[:200] + ("…" if len(prompt_text) > 200 else "")
    yaml_path = f"projects/latent_systems/tool_build/_data/prompts/{prompt_id}.yaml"

    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO prompts (
                    id, concept_id, tool, text_preview, status, failure_reason,
                    drafted_by, discipline_version, yaml_path, created
                ) VALUES (?, ?, ?, ?, 'draft', NULL, ?, ?, ?, ?)
                """,
                (prompt_id, concept_id, tool, text_preview, drafted_by,
                 discipline_version, yaml_path, now),
            )
    finally:
        conn.close()

    # Write source-of-truth YAML (per AD-5).
    yaml_abs = db.DATA_DIR / "prompts" / f"{prompt_id}.yaml"
    yaml_abs.parent.mkdir(parents=True, exist_ok=True)
    import yaml as _yaml
    payload: dict = {
        "id": prompt_id,
        "concept_id": concept_id,
        "tool": tool,
        "text": prompt_text,  # full text in YAML; preview in DB
        "status": "draft",
        "drafted_by": drafted_by,
        "discipline_version": discipline_version,
        "created": now,
    }
    if concept_text is not None:
        payload["concept_text"] = concept_text  # for retry reconstruction
    with yaml_abs.open("w", encoding="utf-8") as f:
        _yaml.safe_dump(payload, f, sort_keys=False,
                        default_flow_style=False, allow_unicode=True)

    return {
        "id": prompt_id, "concept_id": concept_id, "tool": tool,
        "text_preview": text_preview, "status": "draft",
        "drafted_by": drafted_by, "discipline_version": discipline_version,
        "yaml_path": yaml_path, "created": now,
    }


def get_prompt_text(prompt_id: str) -> Optional[str]:
    """Read full prompt text from its YAML representation."""
    yaml_abs = db.DATA_DIR / "prompts" / f"{prompt_id}.yaml"
    if not yaml_abs.exists():
        return None
    import yaml as _yaml
    data = _yaml.safe_load(yaml_abs.read_text(encoding="utf-8"))
    return data.get("text") if data else None


# --- Day 11 Week 3 — API-driven prompt drafting (Feature 2 via Claude API) ---


_DRAFTING_SYSTEM_TEMPLATE = """You are a prompt drafter for LATENT SYSTEMS, an AI-native YouTube documentary channel produced via an AI-only pipeline. Your job: given a concept, draft a tool-specific generation prompt that follows the project's craft discipline.

LATENT SYSTEMS context:
- Documentary register, 16:9 channel format
- Register-disciplined: cold observational, calm-observational; never performative-ominous, never movie-trailer
- Single era / single register per render — no period mixing
- One concept per render — no thesis-image overload

For {tool} prompts, apply this tool-grammar config:

```yaml
{tool_grammar_yaml}
```

Drafting rules:
- Apply syntax_rules unconditionally unless the concept overrides them
- Check vocabulary_priors first; prefer phrases with confidence=high
- Run failure_modes check before finalizing — actively avoid each trigger
- For novel composite subjects, apply novel-concept-resistance mitigation aggressively (explicit negation of MJ defaults + redundant compositional anchoring)
- Lead with subject, then setting, then register
- Length target: 50-80 words for atmospheric photographic register; up to 90 for high-density apparatus; never above 100

OUTPUT FORMAT:
Return ONLY the prompt text, ready to paste into {tool} as-is. Include the syntax_rule flags (e.g., --ar 16:9 --v 7 for MJ). No preamble. No commentary. No markdown fences. Just the prompt string."""


def _classify_llm_failure(e) -> str:
    """Map an llm.LLMError to a failure_type string for the retry queue.
    Reads the api_calls.status the wrapper already wrote; falls back to
    string inspection if that lookup fails."""
    if e.api_call_id:
        conn = db.connect()
        try:
            row = conn.execute(
                "SELECT status FROM api_calls WHERE id = ?", (e.api_call_id,),
            ).fetchone()
        finally:
            conn.close()
        if row and row[0]:
            return row[0]
    # Fallback heuristics.
    msg = str(e).lower()
    if "rate" in msg:
        return "rate_limited"
    if "auth" in msg:
        return "auth_failed"
    if "timeout" in msg:
        return "timeout"
    if "connection" in msg:
        return "network_error"
    return "bad_request"


def _extract_retry_after(e) -> Optional[float]:
    """Pull retry_after seconds from a RateLimitError if available."""
    sdk_err = getattr(e, "sdk_error", None)
    if sdk_err is None:
        return None
    response = getattr(sdk_err, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def retry_prompt(prompt_id: str) -> dict:
    """Manual or auto-triggered retry for a failed prompt. Reads the
    saved concept_text from the prompt YAML and re-issues the API call.

    Used for:
      - 3a.4 timeout — Joseph clicks retry in UI
      - 3a.5 network_error — fallback after auto-retry exhausts
      - 3a.6 bad_request — Joseph clicks retry after fixing whatever
      - 3a.1 rate_limited — both auto-retry processor and manual UI use this

    Re-uses the existing prompt row (no duplicate); creates a NEW api_calls
    row for the retry attempt. On success, updates prompt with the draft;
    on failure, updates prompt status + re-enqueues if still retryable.
    """
    import llm
    import seeds_loader
    import retry_queue as _rq
    import yaml as _yaml

    yaml_abs = db.DATA_DIR / "prompts" / f"{prompt_id}.yaml"
    if not yaml_abs.exists():
        return {"ok": False, "error": f"prompt {prompt_id} yaml missing"}
    data = _yaml.safe_load(yaml_abs.read_text(encoding="utf-8")) or {}
    concept_text = data.get("concept_text")
    tool = data.get("tool", "midjourney")
    if not concept_text:
        return {"ok": False,
                "error": f"prompt {prompt_id} has no concept_text — cannot reconstruct API call"}

    seed_tool = "mj" if tool == "midjourney" else tool
    tool_grammar_yaml = seeds_loader.get_tool_grammar_yaml(seed_tool)
    system = _DRAFTING_SYSTEM_TEMPLATE.format(
        tool=tool, tool_grammar_yaml=tool_grammar_yaml,
    )

    try:
        response = llm.call_claude(
            system=system,
            user_message=f"Concept:\n\n{concept_text}",
            purpose="prompt_drafting_retry",
            prompt_id=prompt_id,
        )
    except llm.LLMError as e:
        failure_status = _classify_llm_failure(e)
        if _rq.is_retryable(failure_status):
            # Update existing queue entry (not a new enqueue — preserves
            # attempt counter; record_attempt_failure handles backoff).
            updated = _rq.record_attempt_failure(
                prompt_id=prompt_id,
                failure_type=failure_status,
                failure_message=str(e),
                retry_after_hint=_extract_retry_after(e),
            )
            if updated is None:
                # Exhausted — promote to permanently failed.
                conn = db.connect()
                try:
                    with conn:
                        conn.execute(
                            "UPDATE prompts SET status = 'failed', failure_reason = ? WHERE id = ?",
                            (f"retries exhausted: {e}", prompt_id),
                        )
                finally:
                    conn.close()
            return {"ok": False, "error": str(e),
                    "failure_type": failure_status,
                    "queue_state": "exhausted" if updated is None else "rescheduled",
                    "retry_after_hint": updated.get("next_attempt_at") if updated else None}
        # Non-retryable: mark prompt failed, remove from queue if present.
        _rq.remove(prompt_id)
        conn = db.connect()
        try:
            with conn:
                conn.execute(
                    "UPDATE prompts SET status = 'failed', failure_reason = ? WHERE id = ?",
                    (str(e), prompt_id),
                )
        finally:
            conn.close()
        return {"ok": False, "error": str(e), "failure_type": failure_status,
                "retryable": False}

    # Success — update prompt + remove from queue.
    draft_text = response.text.strip()
    text_preview = draft_text[:200] + ("…" if len(draft_text) > 200 else "")
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                "UPDATE prompts SET text_preview = ?, status = 'draft', "
                "drafted_by = ?, failure_reason = NULL WHERE id = ?",
                (text_preview, response.model, prompt_id),
            )
    finally:
        conn.close()

    data["text"] = draft_text
    data["status"] = "draft"
    data["drafted_by"] = response.model
    data["api_call_id"] = response.api_call_id
    data["draft_metadata"] = {
        "tokens_in": response.tokens_input,
        "tokens_out": response.tokens_output,
        "cache_read_tokens": response.cache_read_tokens,
        "cache_creation_tokens": response.cache_creation_tokens,
        "cost_usd": response.cost_usd,
        "latency_s": response.latency_s,
    }
    with yaml_abs.open("w", encoding="utf-8") as f:
        _yaml.safe_dump(data, f, sort_keys=False,
                        default_flow_style=False, allow_unicode=True)

    _rq.record_attempt_success(prompt_id)

    return {
        "ok": True,
        "prompt_id": prompt_id,
        "draft_text": draft_text,
        "model": response.model,
        "cost_usd": response.cost_usd,
        "latency_s": response.latency_s,
        "api_call_id": response.api_call_id,
    }


def draft_via_api(
    *, concept_text: str, tool: str = "midjourney",
    concept_id: Optional[str] = None,
) -> dict:
    """Draft a tool-specific prompt via Claude API using the loaded tool-grammar
    config as cached system context.

    Creates a prompts row with drafted_by=<model>, status='draft',
    discipline_version=CURRENT_DISCIPLINE_VERSION. The returned api_call_id
    correlates with the api_calls audit row for cost tracking.

    Returns: {prompt_id, draft_text, model, tokens_in, tokens_out,
              cache_read_tokens, cache_creation_tokens, cost_usd, latency_s,
              api_call_id}.

    Raises llm.LLMError on API failure (api_calls row is updated with the
    failure status; caller decides whether to retry).
    """
    import llm
    import seeds_loader

    # Map dispatcher's tool key to the seed file naming. (dispatcher uses
    # "midjourney" in TOOL_URLS; seed file is mj.yaml.)
    seed_tool = "mj" if tool == "midjourney" else tool
    tool_grammar_yaml = seeds_loader.get_tool_grammar_yaml(seed_tool)

    system = _DRAFTING_SYSTEM_TEMPLATE.format(
        tool=tool, tool_grammar_yaml=tool_grammar_yaml,
    )

    # Pre-create the draft prompt row so the api_calls FK lands on a real ID.
    # Store concept_text in YAML so retry_prompt() can reconstruct the call
    # without an external queue payload.
    record = create_prompt(
        prompt_text="(awaiting draft)",
        tool=tool, concept_id=concept_id,
        drafted_by="claude-opus-4-7",
        concept_text=concept_text,
    )
    prompt_id = record["id"]

    try:
        response = llm.call_claude(
            system=system,
            user_message=f"Concept:\n\n{concept_text}",
            purpose="prompt_drafting",
            prompt_id=prompt_id,
        )
    except llm.LLMError as e:
        # Update the pre-created prompt to reflect failure + classify.
        # Retryable failures (3a.1 rate_limited, 3a.5 network, 3a.4 timeout,
        # server_error) get auto-enqueued. Non-retryable (auth_failed,
        # bad_request) stay 'failed' until manual retry.
        import retry_queue as _rq
        failure_status = _classify_llm_failure(e)
        new_prompt_status = (
            "awaiting_retry" if _rq.is_retryable(failure_status) else "failed"
        )
        conn = db.connect()
        try:
            with conn:
                conn.execute(
                    "UPDATE prompts SET status = ?, failure_reason = ? WHERE id = ?",
                    (new_prompt_status, str(e), prompt_id),
                )
        finally:
            conn.close()

        if _rq.is_retryable(failure_status):
            retry_after = _extract_retry_after(e)
            _rq.enqueue(
                prompt_id=prompt_id,
                api_call_id=e.api_call_id or "unknown",
                failure_type=failure_status,
                failure_message=str(e),
                retry_after_hint=retry_after,
            )
        raise

    draft_text = response.text.strip()

    # Update the prompt row + YAML with the actual draft.
    text_preview = draft_text[:200] + ("…" if len(draft_text) > 200 else "")
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                "UPDATE prompts SET text_preview = ?, drafted_by = ? WHERE id = ?",
                (text_preview, response.model, prompt_id),
            )
    finally:
        conn.close()

    yaml_abs = db.DATA_DIR / "prompts" / f"{prompt_id}.yaml"
    if yaml_abs.exists():
        import yaml as _yaml
        data = _yaml.safe_load(yaml_abs.read_text(encoding="utf-8")) or {}
        data["text"] = draft_text
        data["drafted_by"] = response.model
        data["api_call_id"] = response.api_call_id
        data["draft_metadata"] = {
            "tokens_in": response.tokens_input,
            "tokens_out": response.tokens_output,
            "cache_read_tokens": response.cache_read_tokens,
            "cache_creation_tokens": response.cache_creation_tokens,
            "cost_usd": response.cost_usd,
            "latency_s": response.latency_s,
        }
        with yaml_abs.open("w", encoding="utf-8") as f:
            _yaml.safe_dump(data, f, sort_keys=False,
                            default_flow_style=False, allow_unicode=True)

    return {
        "prompt_id": prompt_id,
        "draft_text": draft_text,
        "model": response.model,
        "tokens_in": response.tokens_input,
        "tokens_out": response.tokens_output,
        "cache_read_tokens": response.cache_read_tokens,
        "cache_creation_tokens": response.cache_creation_tokens,
        "cost_usd": response.cost_usd,
        "latency_s": response.latency_s,
        "api_call_id": response.api_call_id,
    }


# --- Day 8 — failure modes 3b.1, 3b.2, 3b.4 (aging) and 3b.5 (inbox) ---


def _parse_iso(ts: str) -> datetime:
    # Tolerate both '...+00:00' and '...Z' suffixes.
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def compute_attempt_age(started_iso: str, attempt_status: str,
                        now: Optional[datetime] = None) -> dict:
    """Derived aging info for one in-flight attempt.

    Returns: {elapsed_s, age_status} where age_status is one of:
        - 'in_flight'       (status==in_flight and elapsed < 30min)
        - 'still_waiting'   (status==in_flight and 30min <= elapsed < 24h)
        - 'stale_check'     (status==in_flight and elapsed >= 24h)
        - 'closed'          (status != in_flight; aging not applicable)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elapsed = (now - _parse_iso(started_iso)).total_seconds()
    if attempt_status != "in_flight":
        return {"elapsed_s": elapsed, "age_status": "closed"}
    if elapsed >= AGE_STALE_CHECK_S:
        age = "stale_check"
    elif elapsed >= AGE_STILL_WAITING_S:
        age = "still_waiting"
    else:
        age = "in_flight"
    return {"elapsed_s": elapsed, "age_status": age}


def awaiting_prompts() -> list[dict]:
    """List prompts in 'awaiting_return' status with their open attempts'
    aging info. Empty list if no prompts are awaiting."""
    out = []
    conn = db.connect()
    try:
        prompts = conn.execute(
            """
            SELECT id, tool, text_preview, status, created
            FROM prompts WHERE status = 'awaiting_return'
            ORDER BY created DESC
            """
        ).fetchall()
        for pr in prompts:
            pid = pr[0]
            attempts = conn.execute(
                """
                SELECT id, attempt_number, started, started_orig, completed,
                       status, trigger_method, notes
                FROM generation_attempts
                WHERE prompt_id = ?
                ORDER BY attempt_number DESC
                """,
                (pid,),
            ).fetchall()
            attempt_list = []
            for a in attempts:
                # Two elapsed times: aging "current waiting clock" from
                # started (which kick_attempt resets), and "true elapsed
                # since dispatch" from started_orig (immutable per §4.7).
                aging = compute_attempt_age(a[2], a[5])
                started_orig = a[3] or a[2]  # fallback for pre-0002 rows
                aging_orig = compute_attempt_age(started_orig, a[5])
                attempt_list.append({
                    "id": a[0], "attempt_number": a[1],
                    "started": a[2], "started_orig": started_orig,
                    "completed": a[4], "status": a[5],
                    "trigger_method": a[6], "notes": a[7],
                    "elapsed_s": round(aging["elapsed_s"], 1),
                    "elapsed_since_dispatch_s": round(aging_orig["elapsed_s"], 1),
                    "age_status": aging["age_status"],
                })
            out.append({
                "id": pid, "tool": pr[1], "text_preview": pr[2],
                "status": pr[3], "created": pr[4],
                "attempts": attempt_list,
            })
    finally:
        conn.close()
    return out


def _get_attempt(conn: sqlite3.Connection, attempt_id: str) -> Optional[tuple]:
    return conn.execute(
        "SELECT id, prompt_id, attempt_number, status FROM generation_attempts WHERE id = ?",
        (attempt_id,),
    ).fetchone()


def _other_in_flight_attempts(conn: sqlite3.Connection,
                              prompt_id: str, exclude_attempt: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) FROM generation_attempts
        WHERE prompt_id = ? AND id != ? AND status = 'in_flight'
        """,
        (prompt_id, exclude_attempt),
    ).fetchone()
    return int(row[0])


def manual_complete_attempt(attempt_id: str,
                            note: Optional[str] = None) -> dict:
    """User asserts the generation worked but auto-detection didn't fire.
    Flips the attempt and prompt statuses; does NOT bind a render
    (Day 9 owns binding). For when Joseph manually pulls a file in.

    Notes-string audit format (Day 5-9 review §4.12 — for future Phase 2
    promotion to a structured attempt_events table):
        ' [<event_kind>] <free-text-payload>'
    Each transition appends; multiple events accumulate space-separated.
    Regex pattern for parsing: `\\[(\\w+)(?:\\s+([^\\]]*))?\\]`
    Known event kinds: manual_complete, failed, kicked at <iso>, bound to render <id>.
    """
    conn = db.connect()
    try:
        with conn:
            row = _get_attempt(conn, attempt_id)
            if row is None:
                return {"ok": False, "error": f"attempt {attempt_id} not found"}
            if row[3] != "in_flight":
                return {"ok": False, "error": f"attempt is {row[3]}, not in_flight"}
            now = _iso_now()
            conn.execute(
                """
                UPDATE generation_attempts
                SET status = 'completed', completed = ?,
                    notes = COALESCE(notes, '') || ' [manual_complete] ' || COALESCE(?, '')
                WHERE id = ?
                """,
                (now, note, attempt_id),
            )
            conn.execute(
                "UPDATE prompts SET status = 'completed' WHERE id = ?",
                (row[1],),
            )
        return {"ok": True, "attempt_id": attempt_id, "prompt_id": row[1],
                "new_attempt_status": "completed", "new_prompt_status": "completed"}
    finally:
        conn.close()


def mark_attempt_failed(attempt_id: str, reason: str) -> dict:
    """Flip attempt to failed. If no other in-flight attempts on the
    same prompt, prompt also goes to 'failed'. Otherwise prompt stays
    'awaiting_return' until the other attempts resolve."""
    conn = db.connect()
    try:
        with conn:
            row = _get_attempt(conn, attempt_id)
            if row is None:
                return {"ok": False, "error": f"attempt {attempt_id} not found"}
            if row[3] != "in_flight":
                return {"ok": False, "error": f"attempt is {row[3]}, not in_flight"}
            now = _iso_now()
            conn.execute(
                """
                UPDATE generation_attempts
                SET status = 'failed', completed = ?,
                    notes = COALESCE(notes, '') || ' [failed] ' || ?
                WHERE id = ?
                """,
                (now, reason, attempt_id),
            )
            others = _other_in_flight_attempts(conn, row[1], attempt_id)
            new_prompt_status = row[1]  # placeholder
            if others == 0:
                conn.execute(
                    "UPDATE prompts SET status = 'failed', failure_reason = ? WHERE id = ?",
                    (reason, row[1]),
                )
                new_prompt_status = "failed"
            else:
                new_prompt_status = "awaiting_return"
        return {"ok": True, "attempt_id": attempt_id, "prompt_id": row[1],
                "new_attempt_status": "failed",
                "new_prompt_status": new_prompt_status,
                "other_in_flight_attempts": others}
    finally:
        conn.close()


def kick_attempt(attempt_id: str) -> dict:
    """User says 'still waiting' — reset the started timer for this
    attempt so the aging derivation re-clocks from now. The attempt
    stays in_flight; only the perceived age changes."""
    conn = db.connect()
    try:
        with conn:
            row = _get_attempt(conn, attempt_id)
            if row is None:
                return {"ok": False, "error": f"attempt {attempt_id} not found"}
            if row[3] != "in_flight":
                return {"ok": False, "error": f"attempt is {row[3]}, not in_flight"}
            now = _iso_now()
            conn.execute(
                """
                UPDATE generation_attempts
                SET started = ?,
                    notes = COALESCE(notes, '') || ' [kicked at ' || ? || ']'
                WHERE id = ?
                """,
                (now, now, attempt_id),
            )
        return {"ok": True, "attempt_id": attempt_id, "new_started": now}
    finally:
        conn.close()


# --- Day 9 — render binding (Feature 3b loop close) ---


def open_attempts() -> list[dict]:
    """List currently in_flight generation_attempts with prompt info.
    Used by the binding picker (3b.6) and tool-mismatch detection (3b.3).
    Ordered most-recent-started DESC."""
    conn = db.connect()
    try:
        rows = conn.execute(
            """
            SELECT a.id, a.prompt_id, a.attempt_number, a.started,
                   a.trigger_method, p.tool, p.text_preview
            FROM generation_attempts a
            JOIN prompts p ON a.prompt_id = p.id
            WHERE a.status = 'in_flight'
            ORDER BY a.started DESC
            """
        ).fetchall()
        return [
            {
                "attempt_id": r[0], "prompt_id": r[1],
                "attempt_number": r[2], "started": r[3],
                "trigger_method": r[4], "tool": r[5],
                "text_preview": r[6],
            }
            for r in rows
        ]
    finally:
        conn.close()


def _update_render_yaml(render_id: str, updates: dict) -> None:
    """Patch the render YAML at _data/renders/<id>.yaml. Idempotent;
    creates a 'binding' subkey + sets top-level fields per updates."""
    yaml_abs = db.DATA_DIR / "renders" / f"{render_id}.yaml"
    if not yaml_abs.exists():
        return  # walker-enumerated pre_v1 renders may not have YAMLs in
                # the post_v1 layout; skip rather than error
    import yaml as _yaml
    data = _yaml.safe_load(yaml_abs.read_text(encoding="utf-8")) or {}
    data.update(updates)
    with yaml_abs.open("w", encoding="utf-8") as f:
        _yaml.safe_dump(data, f, sort_keys=False,
                        default_flow_style=False, allow_unicode=True)


def bind_render_to_attempt(
    render_id: str, attempt_id: str, *, force: bool = False,
) -> dict:
    """Bind a render to a specific generation_attempt.

    Updates renders.attempt_id + prompt_id; transitions attempt status
    to 'completed' and prompt status to 'completed'. Refuses to bind on
    tool mismatch unless force=True (bypass for 3b.3 'bind anyway').
    """
    conn = db.connect()
    try:
        with conn:
            render = conn.execute(
                "SELECT id, tool, attempt_id FROM renders WHERE id = ?",
                (render_id,),
            ).fetchone()
            if render is None:
                return {"ok": False, "error": f"render {render_id} not found"}
            if render[2] is not None:
                return {"ok": False,
                        "error": f"render already bound to attempt {render[2]}"}

            attempt = conn.execute(
                """
                SELECT a.id, a.prompt_id, a.status, p.tool
                FROM generation_attempts a
                JOIN prompts p ON a.prompt_id = p.id
                WHERE a.id = ?
                """,
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                return {"ok": False, "error": f"attempt {attempt_id} not found"}
            if attempt[2] != "in_flight":
                return {"ok": False,
                        "error": f"attempt is {attempt[2]}, not in_flight"}

            tool_match = (render[1] == attempt[3])
            if not tool_match and not force:
                return {
                    "ok": False, "error": "tool_mismatch",
                    "render_tool": render[1], "attempt_tool": attempt[3],
                    "hint": "pass force=true to bind anyway (3b.3)",
                }

            now = _iso_now()
            prompt_id = attempt[1]
            conn.execute(
                "UPDATE renders SET attempt_id = ?, prompt_id = ? WHERE id = ?",
                (attempt_id, prompt_id, render_id),
            )
            conn.execute(
                """
                UPDATE generation_attempts
                SET status = 'completed', completed = ?,
                    notes = COALESCE(notes, '') || ' [bound to render ' || ? || ']'
                WHERE id = ?
                """,
                (now, render_id, attempt_id),
            )
            conn.execute(
                "UPDATE prompts SET status = 'completed' WHERE id = ?",
                (prompt_id,),
            )

        _update_render_yaml(render_id, {
            "attempt_id": attempt_id,
            "prompt_id": prompt_id,
            "binding": {
                "method": "force" if (not tool_match and force) else "tool_match",
                "bound_at": now,
                "tool_mismatch_overridden": (not tool_match and force),
            },
        })

        return {
            "ok": True, "render_id": render_id,
            "attempt_id": attempt_id, "prompt_id": prompt_id,
            "tool_match": tool_match,
            "force": force,
        }
    finally:
        conn.close()


def auto_bind_render(render_id: str) -> dict:
    """Decide whether to auto-bind a freshly-ingested render.

    Decision matrix per Section 1 / Day 9:
      - 1 in_flight attempt with matching tool -> bind
      - 1 in_flight attempt with tool mismatch  -> 'tool_mismatch' (no bind)
      - 2+ in_flight attempts                   -> 'multiple_open_attempts' (no bind)
      - 0 in_flight attempts                    -> 'orphan' (no bind)

    No-bind cases stamp the render YAML with needs_review_reason so the
    unbound_renders endpoint can surface them. Returns summary dict.
    """
    conn = db.connect()
    try:
        render = conn.execute(
            "SELECT id, tool, attempt_id FROM renders WHERE id = ?",
            (render_id,),
        ).fetchone()
        if render is None:
            return {"ok": False, "decision": "render_not_found"}
        if render[2] is not None:
            return {"ok": True, "decision": "already_bound",
                    "render_id": render_id, "attempt_id": render[2]}

        render_tool = render[1]
        attempts = conn.execute(
            """
            SELECT a.id, a.prompt_id, p.tool
            FROM generation_attempts a
            JOIN prompts p ON a.prompt_id = p.id
            WHERE a.status = 'in_flight'
            ORDER BY a.started DESC
            """
        ).fetchall()
    finally:
        conn.close()

    n = len(attempts)
    if n == 0:
        _update_render_yaml(render_id, {"needs_review_reason": "orphan"})
        return {"ok": True, "decision": "orphan", "render_id": render_id}

    if n == 1:
        att_id, prompt_id, attempt_tool = attempts[0]
        if attempt_tool == render_tool:
            result = bind_render_to_attempt(render_id, att_id, force=False)
            return {"ok": result["ok"], "decision": "auto_bound",
                    "render_id": render_id, "bind_result": result}
        else:
            _update_render_yaml(render_id, {
                "needs_review_reason": "tool_mismatch",
                "candidate_attempt_id": att_id,
                "candidate_attempt_tool": attempt_tool,
            })
            return {"ok": True, "decision": "tool_mismatch",
                    "render_id": render_id,
                    "candidate_attempt_id": att_id,
                    "render_tool": render_tool,
                    "attempt_tool": attempt_tool}

    # 2+ open attempts
    candidate = attempts[0]  # most-recent
    _update_render_yaml(render_id, {
        "needs_review_reason": "multiple_open_attempts",
        "default_candidate_attempt_id": candidate[0],
        "open_attempt_count": n,
    })
    return {"ok": True, "decision": "multiple_open_attempts",
            "render_id": render_id,
            "default_candidate_attempt_id": candidate[0],
            "open_attempt_count": n}


def unbound_renders(*, limit: int = 100) -> list[dict]:
    """List post-v1 renders that arrived via router but didn't auto-bind.
    Reads needs_review_reason from each render's YAML where present.
    """
    out = []
    conn = db.connect()
    try:
        rows = conn.execute(
            """
            SELECT id, filename, filepath, tool, hero_status, created
            FROM renders
            WHERE attempt_id IS NULL
              AND discipline_version = '1.0'
            ORDER BY created DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    import yaml as _yaml
    for r in rows:
        render_id = r[0]
        yaml_abs = db.DATA_DIR / "renders" / f"{render_id}.yaml"
        reason = None
        candidate_attempt_id = None
        open_count = None
        if yaml_abs.exists():
            try:
                data = _yaml.safe_load(yaml_abs.read_text(encoding="utf-8")) or {}
                reason = data.get("needs_review_reason")
                candidate_attempt_id = (data.get("candidate_attempt_id")
                                        or data.get("default_candidate_attempt_id"))
                open_count = data.get("open_attempt_count")
            except Exception:
                pass
        out.append({
            "id": render_id, "filename": r[1], "filepath": r[2],
            "tool": r[3], "hero_status": r[4], "created": r[5],
            "needs_review_reason": reason,
            "candidate_attempt_id": candidate_attempt_id,
            "open_attempt_count": open_count,
        })
    return out


def mark_render_orphan(render_id: str, note: Optional[str] = None) -> dict:
    """Explicitly stamp a render as orphan (no binding desired). Useful
    for renders that arrived from out-of-band sources or that the user
    confirms aren't from any v1 dispatch.
    """
    _update_render_yaml(render_id, {
        "needs_review_reason": "orphan_confirmed",
        "orphan_confirmed_note": note,
        "orphan_confirmed_at": _iso_now(),
    })
    return {"ok": True, "render_id": render_id,
            "needs_review_reason": "orphan_confirmed"}


# --- Day 13 — Feature 9: discipline-drift query surface (per spec F10) ---


# Tables that carry per-row discipline_version (or analogous). Each entry:
# (table, version_column, friendly_name).
DISCIPLINE_TABLES = (
    ("concepts",            "discipline_version",   "concepts"),
    ("prompts",             "discipline_version",   "prompts"),
    ("renders",             "discipline_version",   "renders"),
    ("verdicts",            "discipline_version",   "verdicts"),
    ("hero_promotions",     "discipline_version",   "hero_promotions"),
    ("lineage_edges",       "valid_from_version",   "lineage_edges"),
    ("cross_ai_captures",   "discipline_version",   "cross_ai_captures"),
)


def discipline_drift_summary() -> dict:
    """Aggregate artifact counts grouped by discipline_version across all
    artifact types.

    Returns:
        {
          "current_baseline": "1.0",
          "versions": {
            "pre_v1": {concepts: 0, prompts: 0, renders: 1698, ...},
            "1.0":    {concepts: 0, prompts: 1, renders: 0,    ...},
          },
          "totals_by_version": {"pre_v1": 1698, "1.0": 1},
          "totals_by_type":    {concepts: 0, prompts: 1, renders: 1698, ...},
        }

    Per spec F10: no auto-upgrade actions; this is visibility only.
    """
    versions: dict[str, dict[str, int]] = {}
    totals_by_type: dict[str, int] = {}

    conn = db.connect()
    try:
        for table, version_col, friendly in DISCIPLINE_TABLES:
            rows = conn.execute(
                f"SELECT {version_col}, COUNT(*) FROM {table} "
                f"WHERE {version_col} IS NOT NULL "
                f"GROUP BY {version_col}"
            ).fetchall()
            type_total = 0
            for ver, count in rows:
                versions.setdefault(ver, {}).setdefault(friendly, 0)
                versions[ver][friendly] += int(count)
                type_total += int(count)
            totals_by_type[friendly] = type_total
    finally:
        conn.close()

    # Fill zero entries so each version has all type keys (cleaner UI).
    type_names = [t[2] for t in DISCIPLINE_TABLES]
    for ver in versions:
        for t in type_names:
            versions[ver].setdefault(t, 0)

    totals_by_version = {
        ver: sum(counts.values()) for ver, counts in versions.items()
    }

    from constants import CURRENT_DISCIPLINE_VERSION
    return {
        "current_baseline": CURRENT_DISCIPLINE_VERSION,
        "versions": versions,
        "totals_by_version": totals_by_version,
        "totals_by_type": totals_by_type,
    }


def discipline_drift_artifacts(version: str, *, limit_per_type: int = 100) -> dict:
    """Return all artifacts authored against a given discipline_version.

    Per spec F10: cross-artifact-type queries surfaced in one place. Used
    by the UI drill-down view ("show me everything at v0.X").
    """
    out: dict[str, list[dict]] = {}
    conn = db.connect()
    try:
        # concepts
        rows = conn.execute(
            "SELECT id, name, ep, section, status, created FROM concepts "
            "WHERE discipline_version = ? ORDER BY created DESC LIMIT ?",
            (version, limit_per_type),
        ).fetchall()
        out["concepts"] = [
            {"id": r[0], "name": r[1], "ep": r[2], "section": r[3],
             "status": r[4], "created": r[5]} for r in rows
        ]
        # prompts
        rows = conn.execute(
            "SELECT id, tool, text_preview, status, drafted_by, created FROM prompts "
            "WHERE discipline_version = ? ORDER BY created DESC LIMIT ?",
            (version, limit_per_type),
        ).fetchall()
        out["prompts"] = [
            {"id": r[0], "tool": r[1], "text_preview": r[2], "status": r[3],
             "drafted_by": r[4], "created": r[5]} for r in rows
        ]
        # renders
        rows = conn.execute(
            "SELECT id, filename, filepath, tool, hero_status, created FROM renders "
            "WHERE discipline_version = ? ORDER BY created DESC LIMIT ?",
            (version, limit_per_type),
        ).fetchall()
        out["renders"] = [
            {"id": r[0], "filename": r[1], "filepath": r[2], "tool": r[3],
             "hero_status": r[4], "created": r[5]} for r in rows
        ]
        # verdicts
        rows = conn.execute(
            "SELECT id, render_id, verdict, audited_by, created FROM verdicts "
            "WHERE discipline_version = ? ORDER BY created DESC LIMIT ?",
            (version, limit_per_type),
        ).fetchall()
        out["verdicts"] = [
            {"id": r[0], "render_id": r[1], "verdict": r[2],
             "audited_by": r[3], "created": r[4]} for r in rows
        ]
        # hero_promotions
        rows = conn.execute(
            "SELECT id, render_id, hero_filepath, reversed_at, created FROM hero_promotions "
            "WHERE discipline_version = ? ORDER BY created DESC LIMIT ?",
            (version, limit_per_type),
        ).fetchall()
        out["hero_promotions"] = [
            {"id": r[0], "render_id": r[1], "hero_filepath": r[2],
             "reversed_at": r[3], "created": r[4]} for r in rows
        ]
        # lineage_edges
        rows = conn.execute(
            "SELECT id, source_type, source_id, target_type, target_id, layer, "
            "valid_to_version, stale_reason, created FROM lineage_edges "
            "WHERE valid_from_version = ? ORDER BY created DESC LIMIT ?",
            (version, limit_per_type),
        ).fetchall()
        out["lineage_edges"] = [
            {"id": r[0], "source_type": r[1], "source_id": r[2],
             "target_type": r[3], "target_id": r[4], "layer": r[5],
             "valid_to_version": r[6], "stale_reason": r[7], "created": r[8]}
            for r in rows
        ]
        # cross_ai_captures
        rows = conn.execute(
            "SELECT id, source, captured FROM cross_ai_captures "
            "WHERE discipline_version = ? ORDER BY captured DESC LIMIT ?",
            (version, limit_per_type),
        ).fetchall()
        out["cross_ai_captures"] = [
            {"id": r[0], "source": r[1], "captured": r[2]} for r in rows
        ]
    finally:
        conn.close()
    return {"version": version, "artifacts": out}


def stale_lineage_edges() -> list[dict]:
    """Lineage edges whose valid_from_version is no longer the current
    baseline. Per spec v0.4 temporal lineage_edges → F12 stale-reference
    inventory becomes implementable here.

    Returns edges where valid_to_version IS NOT NULL (explicitly stale)
    OR valid_from_version != current baseline (implicitly stale until proven
    valid). Phase 1 surface; Phase 2 may auto-mark edges stale on bump.
    """
    from constants import CURRENT_DISCIPLINE_VERSION
    conn = db.connect()
    try:
        rows = conn.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id, layer,
                   valid_from_version, valid_to_version, stale_reason, created
            FROM lineage_edges
            WHERE valid_to_version IS NOT NULL
               OR valid_from_version != ?
            ORDER BY created DESC
            """,
            (CURRENT_DISCIPLINE_VERSION,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "source_type": r[1], "source_id": r[2],
         "target_type": r[3], "target_id": r[4], "layer": r[5],
         "valid_from_version": r[6], "valid_to_version": r[7],
         "stale_reason": r[8], "created": r[9]}
        for r in rows
    ]


# --- Day 13 — cost tracking dashboard expansion ---


# --- Day 14 — Feature 1: Concept CRUD ---


CONCEPT_STATUS_VALUES = ("drafting", "generating", "evaluated", "locked", "archived")
# Substantive fields — edits to these bump discipline_version per spec F10.
# Status transitions are workflow events, not concept revisions.
SUBSTANTIVE_CONCEPT_FIELDS = {"name", "subject", "register", "ep", "section"}


def _concept_id_from(name: str, ep: Optional[str], section: Optional[str], iso: str) -> str:
    import hashlib
    seed = f"{name}|{ep or ''}|{section or ''}|{iso}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _write_concept_yaml(record: dict) -> None:
    yaml_abs = db.DATA_DIR / "concepts" / f"{record['id']}.yaml"
    yaml_abs.parent.mkdir(parents=True, exist_ok=True)
    import yaml as _yaml
    with yaml_abs.open("w", encoding="utf-8") as f:
        _yaml.safe_dump(record, f, sort_keys=False,
                        default_flow_style=False, allow_unicode=True)


def create_concept(
    *, name: str,
    ep: Optional[str] = None, section: Optional[str] = None,
    subject: Optional[str] = None, register: Optional[str] = None,
    status: str = "drafting",
    discipline_version: str = CURRENT_DISCIPLINE_VERSION,
) -> dict:
    """Create a new concept. Returns the new record."""
    if not name.strip():
        raise ValueError("concept name is required")
    if status not in CONCEPT_STATUS_VALUES:
        raise ValueError(f"invalid status '{status}'; expected one of {CONCEPT_STATUS_VALUES}")
    now = _iso_now()
    concept_id = _concept_id_from(name, ep, section, now)
    yaml_path = f"projects/latent_systems/tool_build/_data/concepts/{concept_id}.yaml"
    record = {
        "id": concept_id, "name": name, "ep": ep, "section": section,
        "subject": subject, "register": register,
        "status": status, "discipline_version": discipline_version,
        "yaml_path": yaml_path,
        "created": now, "modified": now,
    }
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO concepts (id, name, ep, section, subject, register,
                                      status, discipline_version, yaml_path,
                                      created, modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (concept_id, name, ep, section, subject, register,
                 status, discipline_version, yaml_path, now, now),
            )
    finally:
        conn.close()
    _write_concept_yaml(record)
    return record


def get_concept(concept_id: str) -> Optional[dict]:
    """Return the concept + its linked artifacts (prompts, renders via
    prompt link, verdicts, hero_promotions). Returns None if not found."""
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT id, name, ep, section, subject, register, status, "
            "discipline_version, yaml_path, created, modified "
            "FROM concepts WHERE id = ?",
            (concept_id,),
        ).fetchone()
        if row is None:
            return None
        record = {
            "id": row[0], "name": row[1], "ep": row[2], "section": row[3],
            "subject": row[4], "register": row[5], "status": row[6],
            "discipline_version": row[7], "yaml_path": row[8],
            "created": row[9], "modified": row[10],
        }
        # Linked prompts.
        prompts = conn.execute(
            "SELECT id, tool, text_preview, status, drafted_by, "
            "discipline_version, created FROM prompts "
            "WHERE concept_id = ? ORDER BY created DESC",
            (concept_id,),
        ).fetchall()
        record["prompts"] = [
            {"id": p[0], "tool": p[1], "text_preview": p[2], "status": p[3],
             "drafted_by": p[4], "discipline_version": p[5], "created": p[6]}
            for p in prompts
        ]
        # Linked renders (via prompt_id).
        renders = conn.execute(
            """
            SELECT r.id, r.filename, r.filepath, r.tool, r.hero_status,
                   r.discipline_version, r.created, r.prompt_id
            FROM renders r
            WHERE r.prompt_id IN (
                SELECT id FROM prompts WHERE concept_id = ?
            )
            ORDER BY r.created DESC
            """,
            (concept_id,),
        ).fetchall()
        record["renders"] = [
            {"id": r[0], "filename": r[1], "filepath": r[2], "tool": r[3],
             "hero_status": r[4], "discipline_version": r[5],
             "created": r[6], "prompt_id": r[7]}
            for r in renders
        ]
        # Verdicts on linked renders.
        verdicts = conn.execute(
            """
            SELECT v.id, v.render_id, v.verdict, v.audited_by,
                   v.discipline_version, v.created
            FROM verdicts v
            WHERE v.render_id IN (
                SELECT r.id FROM renders r
                WHERE r.prompt_id IN (SELECT id FROM prompts WHERE concept_id = ?)
            )
            ORDER BY v.created DESC
            """,
            (concept_id,),
        ).fetchall()
        record["verdicts"] = [
            {"id": v[0], "render_id": v[1], "verdict": v[2],
             "audited_by": v[3], "discipline_version": v[4], "created": v[5]}
            for v in verdicts
        ]
        # Hero promotions on linked renders.
        heroes = conn.execute(
            """
            SELECT h.id, h.render_id, h.hero_filepath, h.reversed_at,
                   h.discipline_version, h.created
            FROM hero_promotions h
            WHERE h.render_id IN (
                SELECT r.id FROM renders r
                WHERE r.prompt_id IN (SELECT id FROM prompts WHERE concept_id = ?)
            )
            ORDER BY h.created DESC
            """,
            (concept_id,),
        ).fetchall()
        record["hero_promotions"] = [
            {"id": h[0], "render_id": h[1], "hero_filepath": h[2],
             "reversed_at": h[3], "discipline_version": h[4], "created": h[5]}
            for h in heroes
        ]
    finally:
        conn.close()
    return record


def list_concepts(
    *, ep: Optional[str] = None, section: Optional[str] = None,
    status: Optional[str] = None, register: Optional[str] = None,
    include_archived: bool = False, limit: int = 200,
) -> list[dict]:
    """Filtered list of concepts. Excludes archived by default."""
    where = []
    params: list = []
    if ep is not None:
        where.append("ep = ?"); params.append(ep)
    if section is not None:
        where.append("section = ?"); params.append(section)
    if status is not None:
        where.append("status = ?"); params.append(status)
    if register is not None:
        where.append("register = ?"); params.append(register)
    if not include_archived and status is None:
        where.append("status != 'archived'")
    sql = (
        "SELECT id, name, ep, section, subject, register, status, "
        "discipline_version, created, modified FROM concepts"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY modified DESC LIMIT ?"
    params.append(limit)

    conn = db.connect()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "name": r[1], "ep": r[2], "section": r[3],
         "subject": r[4], "register": r[5], "status": r[6],
         "discipline_version": r[7], "created": r[8], "modified": r[9]}
        for r in rows
    ]


def update_concept(concept_id: str, *, fields: dict) -> dict:
    """Update concept fields. Substantive edits (name/subject/register/ep/section)
    bump `discipline_version` to CURRENT_DISCIPLINE_VERSION per spec F10. Status
    transitions don't bump.

    Returns the updated record. Raises if concept missing.
    """
    if not fields:
        raise ValueError("fields dict is empty")
    allowed = {"name", "ep", "section", "subject", "register", "status"}
    bad = set(fields.keys()) - allowed
    if bad:
        raise ValueError(f"unknown fields: {bad}")
    if "status" in fields and fields["status"] not in CONCEPT_STATUS_VALUES:
        raise ValueError(f"invalid status '{fields['status']}'")

    now = _iso_now()
    substantive = bool(set(fields.keys()) & SUBSTANTIVE_CONCEPT_FIELDS)
    set_clauses = [f"{k} = ?" for k in fields.keys()]
    params: list = list(fields.values())
    set_clauses.append("modified = ?")
    params.append(now)
    if substantive:
        set_clauses.append("discipline_version = ?")
        params.append(CURRENT_DISCIPLINE_VERSION)
    params.append(concept_id)

    conn = db.connect()
    try:
        with conn:
            cur = conn.execute(
                f"UPDATE concepts SET {', '.join(set_clauses)} WHERE id = ?",
                tuple(params),
            )
            if cur.rowcount == 0:
                raise ValueError(f"concept {concept_id} not found")
    finally:
        conn.close()

    record = get_concept(concept_id)
    # Drop the joined artifacts from YAML payload — store the bare concept
    # record only (artifacts are state.db-derived, regenerable on read).
    bare = {k: v for k, v in record.items()
            if k not in ("prompts", "renders", "verdicts", "hero_promotions")}
    _write_concept_yaml(bare)
    return record


def archive_concept(concept_id: str) -> dict:
    """Soft-archive: status='archived'. Concept and linked artifacts stay
    in state.db; archived concepts are excluded from list_concepts by default."""
    return update_concept(concept_id, fields={"status": "archived"})


# --- Day 15 — Phase 1 acceptance: F1 (render→prompt) + F4 (lineage) ---


def get_render_detail(render_id: str) -> Optional[dict]:
    """F1 satisfaction: given render_id, return the render + the prompt
    that produced it + the concept that informed the prompt. Single
    state.db query path; returns None if not found.

    For pre_v1 renders (per AD-3 forward-only), `prompt` is None — that's
    the documented limit of F1's scope.
    """
    conn = db.connect()
    try:
        r = conn.execute(
            """
            SELECT id, attempt_id, prompt_id, filename, filepath,
                   download_hash, canonical_hash, tool, variant,
                   hero_status, discipline_version, yaml_path, created
            FROM renders WHERE id = ?
            """,
            (render_id,),
        ).fetchone()
        if r is None:
            return None
        record = {
            "id": r[0], "attempt_id": r[1], "prompt_id": r[2],
            "filename": r[3], "filepath": r[4],
            "download_hash": r[5], "canonical_hash": r[6],
            "tool": r[7], "variant": r[8], "hero_status": r[9],
            "discipline_version": r[10], "yaml_path": r[11],
            "created": r[12],
            "prompt": None, "concept": None,
        }
        if r[2]:  # prompt_id set
            p = conn.execute(
                """
                SELECT id, concept_id, tool, text_preview, status,
                       drafted_by, discipline_version, created
                FROM prompts WHERE id = ?
                """,
                (r[2],),
            ).fetchone()
            if p:
                record["prompt"] = {
                    "id": p[0], "concept_id": p[1], "tool": p[2],
                    "text_preview": p[3], "status": p[4],
                    "drafted_by": p[5], "discipline_version": p[6],
                    "created": p[7],
                }
                if p[1]:  # concept_id set
                    c = conn.execute(
                        """
                        SELECT id, name, ep, section, subject, register,
                               status, discipline_version, created, modified
                        FROM concepts WHERE id = ?
                        """,
                        (p[1],),
                    ).fetchone()
                    if c:
                        record["concept"] = {
                            "id": c[0], "name": c[1], "ep": c[2], "section": c[3],
                            "subject": c[4], "register": c[5], "status": c[6],
                            "discipline_version": c[7], "created": c[8],
                            "modified": c[9],
                        }
    finally:
        conn.close()
    return record


def lineage_for_artifact(artifact_type: str, artifact_id: str) -> dict:
    """F4 satisfaction: return all lineage edges where this artifact is
    a source (outgoing — what it anchors against) OR a target (incoming
    — what cites it as anchor).

    Returns:
        {
          "artifact_type": "...",
          "artifact_id": "...",
          "outgoing": [edges where source = (type, id)],
          "incoming": [edges where target = (type, id)],
        }

    Each edge includes source/target artifact summaries so callers can
    render lineage chains without follow-up queries.
    """
    conn = db.connect()
    try:
        outgoing = conn.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id,
                   layer, valid_from_version, valid_to_version, stale_reason, created
            FROM lineage_edges
            WHERE source_type = ? AND source_id = ?
            ORDER BY created DESC
            """,
            (artifact_type, artifact_id),
        ).fetchall()
        incoming = conn.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id,
                   layer, valid_from_version, valid_to_version, stale_reason, created
            FROM lineage_edges
            WHERE target_type = ? AND target_id = ?
            ORDER BY created DESC
            """,
            (artifact_type, artifact_id),
        ).fetchall()
    finally:
        conn.close()

    def _row_to_dict(row) -> dict:
        return {
            "id": row[0], "source_type": row[1], "source_id": row[2],
            "target_type": row[3], "target_id": row[4],
            "layer": row[5], "valid_from_version": row[6],
            "valid_to_version": row[7], "stale_reason": row[8],
            "created": row[9],
        }

    return {
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "outgoing": [_row_to_dict(r) for r in outgoing],
        "incoming": [_row_to_dict(r) for r in incoming],
    }


def create_lineage_edge(
    *, source_type: str, source_id: str,
    target_type: str, target_id: str,
    layer: int,
    valid_from_version: str = CURRENT_DISCIPLINE_VERSION,
) -> dict:
    """Create a lineage_edges row. Layer per spec M4:
      1 = render → render (craft-vocabulary citations)
      2 = concept → concept (chat-derived idea inheritance)
      3 = channel-arch → ep-arch → notes.md (structural inheritance)

    Stable id: sha256(source|target|layer|valid_from)[:16].
    """
    if layer not in (1, 2, 3):
        raise ValueError(f"layer must be 1/2/3, got {layer}")
    import hashlib
    seed = f"{source_type}:{source_id}|{target_type}:{target_id}|{layer}|{valid_from_version}"
    edge_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    now = _iso_now()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO lineage_edges (id, source_type, source_id,
                                           target_type, target_id, layer,
                                           valid_from_version, valid_to_version,
                                           stale_reason, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
                """,
                (edge_id, source_type, source_id, target_type, target_id,
                 layer, valid_from_version, now),
            )
    finally:
        conn.close()
    return {
        "id": edge_id, "source_type": source_type, "source_id": source_id,
        "target_type": target_type, "target_id": target_id,
        "layer": layer, "valid_from_version": valid_from_version,
        "created": now,
    }


# --- Day 13 — cost tracking dashboard expansion ---


def cost_breakdown() -> dict:
    """Aggregate api_calls cost across rolling windows + by purpose.
    Returns:
        {
          "today_usd": <float>,
          "past_7d_usd": <float>,
          "past_30d_usd": <float>,
          "by_purpose": {"prompt_drafting": <float>, ...},
          "by_status_30d": {"succeeded": <count>, "rate_limited": <count>, ...},
          "total_calls_30d": <int>,
          "total_tokens_30d_in": <int>,
          "total_tokens_30d_out": <int>,
        }
    """
    conn = db.connect()
    try:
        # Rolling windows.
        today = conn.execute(
            "SELECT COALESCE(SUM(cost_usd_estimate), 0) FROM api_calls "
            "WHERE started >= datetime('now', 'start of day')"
        ).fetchone()[0]
        past_7d = conn.execute(
            "SELECT COALESCE(SUM(cost_usd_estimate), 0) FROM api_calls "
            "WHERE started >= datetime('now', '-7 days')"
        ).fetchone()[0]
        past_30d = conn.execute(
            "SELECT COALESCE(SUM(cost_usd_estimate), 0) FROM api_calls "
            "WHERE started >= datetime('now', '-30 days')"
        ).fetchone()[0]

        # By purpose, last 30d.
        by_purpose_rows = conn.execute(
            "SELECT purpose, COALESCE(SUM(cost_usd_estimate), 0) FROM api_calls "
            "WHERE started >= datetime('now', '-30 days') "
            "AND status = 'succeeded' "
            "GROUP BY purpose"
        ).fetchall()
        by_purpose = {p: round(c, 4) for p, c in by_purpose_rows}

        # By status, last 30d.
        by_status_rows = conn.execute(
            "SELECT status, COUNT(*) FROM api_calls "
            "WHERE started >= datetime('now', '-30 days') "
            "GROUP BY status"
        ).fetchall()
        by_status = {s: int(n) for s, n in by_status_rows}

        # Totals.
        totals = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(tokens_in), 0), COALESCE(SUM(tokens_out), 0) "
            "FROM api_calls WHERE started >= datetime('now', '-30 days') "
            "AND status = 'succeeded'"
        ).fetchone()
    finally:
        conn.close()

    return {
        "today_usd": round(today or 0, 4),
        "past_7d_usd": round(past_7d or 0, 4),
        "past_30d_usd": round(past_30d or 0, 4),
        "by_purpose": by_purpose,
        "by_status_30d": by_status,
        "total_calls_30d": int(totals[0] or 0),
        "total_tokens_30d_in": int(totals[1] or 0),
        "total_tokens_30d_out": int(totals[2] or 0),
    }


def inbox_renders(*, limit: int = 50) -> list[dict]:
    """List renders that the router routed to inbox/unclassified
    destinations (3b.5). These are low-confidence routes the user
    should review.
    """
    conn = db.connect()
    try:
        # Build a WHERE clause matching any of the inbox fragments.
        where_clauses = " OR ".join(["filepath LIKE ?"] * len(INBOX_PATH_FRAGMENTS))
        params: list = [f"%{frag}%" for frag in INBOX_PATH_FRAGMENTS]
        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT id, filename, filepath, tool, hero_status,
                   discipline_version, created
            FROM renders
            WHERE ({where_clauses})
            ORDER BY created DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [
            {
                "id": r[0], "filename": r[1], "filepath": r[2],
                "tool": r[3], "hero_status": r[4],
                "discipline_version": r[5], "created": r[6],
            }
            for r in rows
        ]
    finally:
        conn.close()
