"""Anthropic SDK wrapper with api_calls instrumentation + cost tracking.

Day 11 (Week 3): substrate for prompt drafting (Feature 2), NOTES.md
authorship (Phase 3 Feature 6), and audit AI consultation (Phase 2
Feature 4). Single entry point call_claude() handles:

  - Request shape (adaptive thinking, ephemeral cache_control on system)
  - Typed-exception handling (RateLimitError, AuthenticationError, etc.)
  - api_calls table row management (per Section 2 schema, Q11 cost tracking)
  - Cost computation from response.usage + MODEL_PRICING

Per claude-api skill defaults: claude-opus-4-7 with adaptive thinking.
SDK auto-retries 429 + 5xx with backoff (max_retries=2 default); we
don't reinvent retry logic.

Failure-mode mapping (Phase 1 design notes Section 1):
  - 3a.1 rate limit -> RateLimitError -> Day 12 retry queue
  - 3a.2 auth error -> AuthenticationError -> no retry, surface modal
  - 3a.4 timeout -> APITimeoutError -> Day 12 manual retry UI
  - 3a.5 network failure -> APIConnectionError -> Day 12 single auto-retry
  - 3a.6 malformed response -> APIStatusError -> Day 12 manual retry UI

Day 11 covers happy path + cost instrumentation. Day 12 layers retry
queue persistence (`_retry_queue.yaml`) and UI surfacing.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import anthropic

import db
from constants import CURRENT_DISCIPLINE_VERSION  # noqa: F401  (re-exported for callers)


DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 16000  # under SDK HTTP timeout for non-streaming


# Per-million-token pricing per claude-api skill cache (2026-04-15 snapshot).
# Cache writes: 1.25x for 5-min TTL (default ephemeral).
# Cache reads:  0.1x.
MODEL_PRICING = {
    "claude-opus-4-7":   {"input": 5.00,  "output": 25.00},
    "claude-opus-4-6":   {"input": 5.00,  "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5":  {"input": 1.00,  "output":  5.00},
}
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


@dataclass
class LLMResponse:
    """Result of a Claude API call."""
    text: str
    model: str
    tokens_input: int
    tokens_output: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    api_call_id: Optional[str] = None
    raw_response: Any = field(default=None, repr=False)


class LLMError(Exception):
    """Wraps an Anthropic SDK exception with the api_calls row id so callers
    can correlate failures with audit log entries."""

    def __init__(self, message: str, *, api_call_id: Optional[str] = None,
                 sdk_error: Optional[Exception] = None,
                 retryable: bool = False) -> None:
        super().__init__(message)
        self.api_call_id = api_call_id
        self.sdk_error = sdk_error
        self.retryable = retryable


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_call_id() -> str:
    return f"call_{uuid.uuid4().hex[:16]}"


def _get_client() -> anthropic.Anthropic:
    """Lazy-init the Anthropic client. Reads ANTHROPIC_API_KEY from env."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError(
            "ANTHROPIC_API_KEY not set in environment. "
            "Add to .env or export before starting the server.",
            retryable=False,
        )
    return anthropic.Anthropic()


def compute_cost(model: str, *, tokens_input: int, tokens_output: int,
                 cache_read: int = 0, cache_creation: int = 0) -> float:
    """Cost in USD per claude-api skill pricing (per-million-token rates).

    Effective input cost = uncached + creation*1.25x + read*0.1x (per million).
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0
    in_rate = pricing["input"] / 1_000_000
    out_rate = pricing["output"] / 1_000_000
    cost_in = (tokens_input * in_rate
               + cache_creation * in_rate * CACHE_WRITE_MULTIPLIER
               + cache_read * in_rate * CACHE_READ_MULTIPLIER)
    cost_out = tokens_output * out_rate
    return round(cost_in + cost_out, 6)


def _insert_api_call_row(
    conn: sqlite3.Connection, *, api_call_id: str, provider: str,
    endpoint: str, purpose: str, prompt_id: Optional[str],
    started: str,
) -> None:
    conn.execute(
        """
        INSERT INTO api_calls (
            id, provider, endpoint, purpose, prompt_id, started, completed,
            status, tokens_in, tokens_out, cost_usd_estimate, error
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, 'in_flight', NULL, NULL, NULL, NULL)
        """,
        (api_call_id, provider, endpoint, purpose, prompt_id, started),
    )


def _update_api_call_succeeded(
    conn: sqlite3.Connection, *, api_call_id: str, completed: str,
    tokens_in: int, tokens_out: int, cost: float,
) -> None:
    conn.execute(
        """
        UPDATE api_calls
        SET completed = ?, status = 'succeeded',
            tokens_in = ?, tokens_out = ?, cost_usd_estimate = ?
        WHERE id = ?
        """,
        (completed, tokens_in, tokens_out, cost, api_call_id),
    )


def _update_api_call_failed(
    conn: sqlite3.Connection, *, api_call_id: str, completed: str,
    status: str, error: str,
) -> None:
    conn.execute(
        """
        UPDATE api_calls
        SET completed = ?, status = ?, error = ?
        WHERE id = ?
        """,
        (completed, status, error, api_call_id),
    )


def call_claude(
    *, system: str, user_message: str,
    purpose: str, prompt_id: Optional[str] = None,
    model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS,
    enable_thinking: bool = True,
    cache_system: bool = True,
) -> LLMResponse:
    """Single-turn Claude call with full instrumentation.

    Returns LLMResponse on success. Raises LLMError on any SDK error;
    api_calls row is updated with status=failed/rate_limited/auth_failed
    and error text. SDK auto-retries 429 + 5xx (max_retries=2 default).

    Args:
      system: full system prompt (the cacheable part — keep stable).
      user_message: the volatile user-turn text (concept, query, etc.).
      purpose: classification for api_calls.purpose ('prompt_drafting',
               'notes_md_authorship', 'audit_consultation', etc.).
      prompt_id: FK to prompts.id if this call is drafting/extending one.
      model: defaults to claude-opus-4-7 per claude-api skill.
      max_tokens: defaults to 16000 (non-streaming SDK timeout headroom).
      enable_thinking: adaptive thinking on Opus 4.7 (default on per skill).
      cache_system: ephemeral cache_control on the system prompt block
                    (cache hits make repeated drafts ~10x cheaper).
    """
    api_call_id = _api_call_id()
    started_iso = _iso_now()
    started_perf = time.perf_counter()

    # 1. Insert in_flight row before the call. If we crash mid-call,
    #    the row's stale status surfaces as an audit-trail anomaly.
    conn = db.connect()
    try:
        with conn:
            _insert_api_call_row(
                conn, api_call_id=api_call_id, provider="anthropic",
                endpoint="messages", purpose=purpose, prompt_id=prompt_id,
                started=started_iso,
            )
    finally:
        conn.close()

    # 2. Build the request. cache_control on system block enables prompt
    #    caching for the (stable) tool-grammar + project context.
    if cache_system:
        system_payload: Any = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
    else:
        system_payload = system

    request_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_payload,
        "messages": [{"role": "user", "content": user_message}],
    }
    if enable_thinking and model.startswith("claude-opus-4-7"):
        # Opus 4.7: adaptive thinking only (no budget_tokens).
        request_kwargs["thinking"] = {"type": "adaptive"}

    # 3. Make the call. SDK handles auto-retry on 429/5xx.
    try:
        client = _get_client()
        response = client.messages.create(**request_kwargs)
    except anthropic.AuthenticationError as e:
        completed = _iso_now()
        conn = db.connect()
        try:
            with conn:
                _update_api_call_failed(
                    conn, api_call_id=api_call_id, completed=completed,
                    status="auth_failed", error=str(e),
                )
        finally:
            conn.close()
        raise LLMError(
            f"Anthropic auth failed: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=False,
        )
    except anthropic.RateLimitError as e:
        completed = _iso_now()
        retry_after = e.response.headers.get("retry-after") if e.response else None
        conn = db.connect()
        try:
            with conn:
                _update_api_call_failed(
                    conn, api_call_id=api_call_id, completed=completed,
                    status="rate_limited",
                    error=f"{e}; retry_after={retry_after}",
                )
        finally:
            conn.close()
        raise LLMError(
            f"Anthropic rate limited (retry_after={retry_after}): {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=True,
        )
    except anthropic.APITimeoutError as e:
        completed = _iso_now()
        conn = db.connect()
        try:
            with conn:
                _update_api_call_failed(
                    conn, api_call_id=api_call_id, completed=completed,
                    status="timeout", error=str(e),
                )
        finally:
            conn.close()
        raise LLMError(
            f"Anthropic timeout: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=True,
        )
    except anthropic.APIConnectionError as e:
        completed = _iso_now()
        conn = db.connect()
        try:
            with conn:
                _update_api_call_failed(
                    conn, api_call_id=api_call_id, completed=completed,
                    status="network_error", error=str(e),
                )
        finally:
            conn.close()
        raise LLMError(
            f"Anthropic connection failed: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=True,
        )
    except anthropic.APIStatusError as e:
        completed = _iso_now()
        status = "server_error" if e.status_code >= 500 else "bad_request"
        conn = db.connect()
        try:
            with conn:
                _update_api_call_failed(
                    conn, api_call_id=api_call_id, completed=completed,
                    status=status, error=f"{e.status_code}: {e.message}",
                )
        finally:
            conn.close()
        raise LLMError(
            f"Anthropic API error ({e.status_code}): {e.message}",
            api_call_id=api_call_id, sdk_error=e, retryable=(e.status_code >= 500),
        )

    # 4. Success path — extract text, compute cost, finalize row.
    latency_s = time.perf_counter() - started_perf
    completed = _iso_now()
    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    text = "".join(text_blocks)

    usage = response.usage
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cost = compute_cost(
        response.model, tokens_input=tokens_in, tokens_output=tokens_out,
        cache_read=cache_read, cache_creation=cache_creation,
    )

    conn = db.connect()
    try:
        with conn:
            _update_api_call_succeeded(
                conn, api_call_id=api_call_id, completed=completed,
                tokens_in=tokens_in + cache_read + cache_creation,
                tokens_out=tokens_out, cost=cost,
            )
    finally:
        conn.close()

    return LLMResponse(
        text=text,
        model=response.model,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_creation,
        cost_usd=cost,
        latency_s=round(latency_s, 3),
        api_call_id=api_call_id,
        raw_response=response,
    )
