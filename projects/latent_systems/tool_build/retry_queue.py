"""Retry queue for transient API failures (3a.1, 3a.5).

Per phase1_design_notes.md Section 1:
  - 3a.1 rate limit: backoff = retry_after if provided, else 60s; double on
    each subsequent 429 up to 600s cap. After 3 consecutive 429s on the
    same prompt, stop auto-retry; surface "rate-limited persistently —
    manual retry available."
  - 3a.5 network failure: single auto-retry after 30s. If second attempt
    fails, stop. UI offers manual retry.

Per spec Section 5: persistence at `tool_build/_data/_retry_queue.yaml`.
Survives app restart. On startup, app resumes pending retries.

Storage layout (YAML):
    version: 0001
    queue:
      - prompt_id: "..."
        api_call_id: "..."           # the failed call (for audit correlation)
        failure_type: "rate_limited" | "network_error" | ...
        failure_message: "..."
        queued_at: "<iso>"
        next_attempt_at: "<iso>"
        attempts: <int>              # how many retries already happened
        max_attempts: <int>
        retry_after_hint: <seconds | null>  # from RateLimitError, if any

The queue is an INDEX into prompts (by prompt_id), not a copy of the request
payload. The prompt YAML stores `concept_text` + `tool`; the retry processor
reads that and reconstructs the API call. Keeps queue small + lets retried
calls pick up an updated tool-grammar config if it changed since the
original failure.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml

import db


QUEUE_FILE = db.DATA_DIR / "_retry_queue.yaml"
QUEUE_VERSION = "0001"

# Per Section 1 / 3a.1 spec.
RATE_LIMIT_INITIAL_BACKOFF_S = 60
RATE_LIMIT_BACKOFF_CAP_S = 600
RATE_LIMIT_MAX_ATTEMPTS = 3

# Per Section 1 / 3a.5 spec.
NETWORK_RETRY_DELAY_S = 30
NETWORK_MAX_ATTEMPTS = 1  # spec: "Single auto-retry after 30s"

# Catch-all for other retryable transient failures (timeout, server_error).
DEFAULT_MAX_ATTEMPTS = 1
DEFAULT_RETRY_DELAY_S = 60

_lock = threading.Lock()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _load() -> dict:
    """Load queue from disk. Returns {version, queue: [...]} dict."""
    if not QUEUE_FILE.exists():
        return {"version": QUEUE_VERSION, "queue": []}
    try:
        data = yaml.safe_load(QUEUE_FILE.read_text(encoding="utf-8")) or {}
        if data.get("version") != QUEUE_VERSION:
            return {"version": QUEUE_VERSION, "queue": []}
        if "queue" not in data or not isinstance(data["queue"], list):
            data["queue"] = []
        return data
    except (OSError, yaml.YAMLError):
        return {"version": QUEUE_VERSION, "queue": []}


def _save(data: dict) -> None:
    """Atomic save via tmp+replace. Caller must hold _lock."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE_FILE.with_suffix(".yaml.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False,
                       default_flow_style=False, allow_unicode=True)
    tmp.replace(QUEUE_FILE)


def compute_backoff(failure_type: str, attempts: int,
                     retry_after_hint: Optional[float] = None) -> tuple[int, int]:
    """Return (delay_seconds, max_attempts) for the failure type.

    Per spec:
      - 3a.1 rate_limited: retry_after if given, else 60s; double per attempt
        (60 -> 120 -> 240 -> 480 -> 600 cap); max 3 attempts.
      - 3a.5 network_error: 30s; max 1 attempt.
      - Other retryable (timeout, server_error): 60s; max 1 attempt.
    """
    if failure_type == "rate_limited":
        if retry_after_hint is not None and attempts == 0:
            delay = max(int(retry_after_hint), RATE_LIMIT_INITIAL_BACKOFF_S)
        else:
            # Double on each subsequent attempt (after first); cap at 600s.
            delay = min(RATE_LIMIT_INITIAL_BACKOFF_S * (2 ** attempts),
                        RATE_LIMIT_BACKOFF_CAP_S)
        return delay, RATE_LIMIT_MAX_ATTEMPTS
    if failure_type == "network_error":
        return NETWORK_RETRY_DELAY_S, NETWORK_MAX_ATTEMPTS
    return DEFAULT_RETRY_DELAY_S, DEFAULT_MAX_ATTEMPTS


def is_retryable(failure_type: str) -> bool:
    """True if this failure type goes into the auto-retry queue. Other
    failures (auth_failed, bad_request) require manual retry."""
    return failure_type in {"rate_limited", "network_error", "timeout", "server_error"}


def enqueue(*, prompt_id: str, api_call_id: str, failure_type: str,
            failure_message: str,
            retry_after_hint: Optional[float] = None) -> Optional[dict]:
    """Add a failed call to the retry queue. Returns the queue entry, or
    None if the failure type isn't retryable."""
    if not is_retryable(failure_type):
        return None
    delay_s, max_attempts = compute_backoff(failure_type, 0, retry_after_hint)
    now = datetime.now(timezone.utc)
    entry = {
        "prompt_id": prompt_id,
        "api_call_id": api_call_id,
        "failure_type": failure_type,
        "failure_message": failure_message,
        "queued_at": now.isoformat(),
        "next_attempt_at": (now + timedelta(seconds=delay_s)).isoformat(),
        "attempts": 0,
        "max_attempts": max_attempts,
        "retry_after_hint": retry_after_hint,
    }
    with _lock:
        data = _load()
        # Replace any existing entry for the same prompt_id (most-recent wins).
        data["queue"] = [e for e in data["queue"] if e.get("prompt_id") != prompt_id]
        data["queue"].append(entry)
        _save(data)
    return entry


def remove(prompt_id: str) -> bool:
    """Remove a prompt's entry from the queue. Returns True if removed."""
    with _lock:
        data = _load()
        before = len(data["queue"])
        data["queue"] = [e for e in data["queue"] if e.get("prompt_id") != prompt_id]
        removed = len(data["queue"]) < before
        if removed:
            _save(data)
    return removed


def list_queue() -> list[dict]:
    """Snapshot of current queue."""
    with _lock:
        data = _load()
        return [dict(e) for e in data["queue"]]


def eligible_for_retry(now: Optional[datetime] = None) -> list[dict]:
    """Entries whose next_attempt_at <= now AND attempts < max_attempts."""
    if now is None:
        now = datetime.now(timezone.utc)
    out = []
    for entry in list_queue():
        try:
            next_ts = _parse_iso(entry["next_attempt_at"])
        except (KeyError, ValueError):
            continue
        if next_ts <= now and entry["attempts"] < entry["max_attempts"]:
            out.append(entry)
    return out


def record_attempt_failure(*, prompt_id: str, failure_type: str,
                           failure_message: str,
                           retry_after_hint: Optional[float] = None) -> Optional[dict]:
    """Record a retry attempt that itself failed. Increments attempts,
    schedules the next attempt with proper backoff. Returns updated entry,
    or None if the entry was exhausted (and will be removed)."""
    with _lock:
        data = _load()
        for i, entry in enumerate(data["queue"]):
            if entry.get("prompt_id") != prompt_id:
                continue
            entry["attempts"] = int(entry.get("attempts", 0)) + 1
            entry["failure_type"] = failure_type  # most-recent failure
            entry["failure_message"] = failure_message
            entry["last_attempt_at"] = _iso_now()
            if entry["attempts"] >= entry["max_attempts"]:
                # Exhausted — remove from queue.
                data["queue"].pop(i)
                _save(data)
                return None
            delay_s, _ = compute_backoff(
                failure_type, entry["attempts"], retry_after_hint,
            )
            now = datetime.now(timezone.utc)
            entry["next_attempt_at"] = (now + timedelta(seconds=delay_s)).isoformat()
            _save(data)
            return entry
    return None


def record_attempt_success(prompt_id: str) -> bool:
    """Remove entry on successful retry. Returns True if entry existed."""
    return remove(prompt_id)
