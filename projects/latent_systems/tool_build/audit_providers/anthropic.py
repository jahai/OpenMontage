"""Anthropic vision API adapter (Phase 2 Wave B baseline provider).

Per phase2_design_notes.md v0.4 §3 (call shape) + §1 4.1-4.12
(failure modes including vision-specific 4.10 safety_refused, 4.11
context_window_exceeded, 4.12 deferred batch).

Mirrors llm.py patterns:
  - api_calls instrumentation (in_flight row at start; succeeded/failed
    update at end with tokens + cost)
  - Typed-exception handling (RateLimitError, AuthenticationError,
    APITimeoutError, APIConnectionError, BadRequestError)
  - Cost computation via llm.compute_cost (same per-million-token rates;
    vision images are billed as image-token-equivalents counted by the
    SDK)
  - Cache-control on system prompt block (rubric is stable across many
    consultations within a session — caching makes repeated audits
    ~10x cheaper on the input side)

Returns VisionConsultationResponse with a status enum (completed,
parse_failed, safety_refused, context_exceeded, partial). Status
discrimination happens HERE rather than at the orchestrator so each
provider can encode its own response-shape quirks (e.g., Anthropic's
"I can't" prefix on policy refusals).

Image input: caller passes a Path. Adapter base64-encodes; supports
JPEG/PNG/WebP/GIF media types. Downscaling responsibility is upstream
(thumbnails.py for cached thumbnails, or audit_consultation
orchestrator if it picks the original render). The `used_downscale`
flag is plumbed through to the consultation record for audit-trail.
"""

from __future__ import annotations

import base64
import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import anthropic

import db
import llm


VISION_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 4000  # structured JSON response; rarely > 1000 tokens

# Safety-refusal detector (failure mode 4.10).
# Anthropic's content-policy refusals start with formulaic phrasing in
# the first ~200 chars. Match conservatively to avoid false positives
# on legitimate critical evaluations ("composition is incoherent" etc).
_SAFETY_REFUSAL_RE = re.compile(
    r"^.{0,200}?(I can't|I cannot|I won't|I will not|"
    r"I'm not able to|I am not able to|"
    r"safety guidelines|content policy|"
    r"unable to (assist|help|process|evaluate))",
    re.IGNORECASE | re.DOTALL,
)

# Image media type lookup by file extension.
_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class VisionError(llm.LLMError):
    """Vision-specific failure that isn't a status-able VisionConsultationResponse —
    typically SDK-level (network, auth, rate limit). Inherits LLMError for
    uniform handling at the orchestrator + retry-queue layer."""


@dataclass
class VisionConsultationResponse:
    """Result of a vision-API audit consultation.

    `status` discriminates the four non-SDK outcomes:
      - 'completed': structured JSON parsed; verdict_inference + criteria_match
      - 'parse_failed': model returned text that couldn't be extracted to JSON
      - 'safety_refused': content-policy refusal detected (4.10)
      - 'context_exceeded': pre-flight check triggered truncation, OR API
                            returned a context-window error post-call
                            (4.11)

    Raw response always preserved (raw_response field) regardless of
    status — caller can surface to Joseph for manual extraction.
    """
    raw_response: str
    parsed: Optional[dict]
    status: str
    cost_usd: float
    tokens_input: int
    tokens_output: int
    used_downscale: bool
    api_call_id: str
    model: str
    failure_reason: Optional[str] = None


# ----------------------------------------------------------------------
# Pure helpers (testable without SDK)
# ----------------------------------------------------------------------

def build_system_prompt(rubric: dict) -> str:
    """Compose system prompt from a parsed rubric (per rubric.parse_rubric_text).

    Output structure: meta header + criteria block. Designed to be
    cache-stable: same rubric → identical text → cache hit on repeat
    consultations within the same audit session.
    """
    lines = [
        "You are auditing a single rendered image against a structured rubric.",
        "Return ONLY a JSON object with these fields (no preamble, no closing remarks):",
        "  verdict_inference: one of \"hero_zone\" | \"strong\" | \"weak\" | \"reject\"",
        "  criteria_match: object mapping each criterion name to one of",
        "    \"pass\" | \"partial\" | \"fail\" | \"not_evaluated\"",
        "  key_observations: array of 1-5 short strings, one observation each",
        "",
        f"Rubric version {rubric['version']} (discipline {rubric['discipline_version']}).",
    ]
    if not rubric["criteria"]:
        lines.append("")
        lines.append("(No criteria defined; use general visual-quality judgment.)")
        return "\n".join(lines)

    lines.append("")
    lines.append("Criteria:")
    for name, c in rubric["criteria"].items():
        lines.append("")
        lines.append(f"### {name}")
        if c["definition"]:
            lines.append(c["definition"])
        if c["pass"]:
            lines.append(f"- pass: {c['pass']}")
        if c["partial"]:
            lines.append(f"- partial: {c['partial']}")
        if c["fail"]:
            lines.append(f"- fail: {c['fail']}")
    return "\n".join(lines)


def build_user_message(
    *, concept_text: Optional[str] = None,
    lineage_summary: Optional[str] = None,
) -> str:
    """Compose the text portion of the user message. Image is added separately."""
    parts: list[str] = []
    if concept_text:
        parts.append(f"Concept context:\n{concept_text}")
    if lineage_summary:
        parts.append(f"Lineage chain:\n{lineage_summary}")
    parts.append("Evaluate the attached image against the rubric.")
    return "\n\n".join(parts)


def encode_image_b64(image_path: Path) -> tuple[str, str]:
    """Return (base64-encoded data, media_type) for an image file.

    Raises ValueError on unsupported extensions, FileNotFoundError on
    missing file (caller resolves before calling).
    """
    if not image_path.exists():
        raise FileNotFoundError(f"image not found: {image_path}")
    media_type = _MEDIA_TYPES.get(image_path.suffix.lower())
    if media_type is None:
        raise ValueError(
            f"unsupported image format {image_path.suffix!r}; "
            f"expected one of {sorted(_MEDIA_TYPES)}"
        )
    with image_path.open("rb") as f:
        data = base64.standard_b64encode(f.read()).decode("ascii")
    return data, media_type


def parse_response_json(text: str) -> Optional[dict]:
    """Parse-tolerant JSON extraction from response text.

    Tries direct json.loads first; if that fails, finds the outermost
    {...} pair and parses that. Returns None if no parseable JSON
    object found — caller maps to status='parse_failed'.
    """
    if not text:
        return None
    stripped = text.strip()
    try:
        result = json.loads(stripped)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    # Surrounding prose? Find outermost { ... }.
    open_idx = stripped.find("{")
    close_idx = stripped.rfind("}")
    if open_idx == -1 or close_idx == -1 or close_idx <= open_idx:
        return None
    try:
        result = json.loads(stripped[open_idx:close_idx + 1])
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        return None
    return None


def detect_safety_refusal(text: str) -> bool:
    """True if the response text starts with an Anthropic content-policy
    refusal pattern (failure mode 4.10)."""
    if not text:
        return False
    return bool(_SAFETY_REFUSAL_RE.match(text))


# ----------------------------------------------------------------------
# Main orchestrator
# ----------------------------------------------------------------------

def call_vision(
    *,
    image_path: Path,
    rubric: dict,
    concept_text: Optional[str] = None,
    lineage_summary: Optional[str] = None,
    used_downscale: bool = False,
    purpose: str = "audit_consultation",
    model: str = VISION_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    cache_system: bool = True,
) -> VisionConsultationResponse:
    """Single-image audit consultation via Anthropic vision.

    Returns VisionConsultationResponse with a status enum:
      - 'completed' on parsed JSON
      - 'parse_failed' on un-parseable model output
      - 'safety_refused' on detected content-policy refusal

    Raises VisionError (subclasses LLMError, retryable=True for transient,
    False for permanent) on SDK-level failures: AuthenticationError,
    RateLimitError, APITimeoutError, APIConnectionError, APIStatusError.
    Caller hands these to the retry queue same as llm.call_claude.

    BadRequestError with 'context' in the message is mapped to a
    VisionConsultationResponse with status='context_exceeded' rather than
    raising, since this is a content-shape problem (truncate lineage,
    retry) not a transient SDK failure.
    """
    api_call_id = llm._api_call_id()
    started_iso = llm._iso_now()
    started_perf = time.perf_counter()

    # 1. Insert in_flight row (bound to a verdict_id at the orchestrator
    # layer; api_calls.prompt_id stays NULL since this isn't drafting a prompt).
    conn = db.connect()
    try:
        with conn:
            llm._insert_api_call_row(
                conn, api_call_id=api_call_id, provider="anthropic",
                endpoint="messages.vision", purpose=purpose, prompt_id=None,
                started=started_iso,
            )
    finally:
        conn.close()

    # 2. Build payload.
    img_b64, media_type = encode_image_b64(image_path)
    system_text = build_system_prompt(rubric)
    user_text = build_user_message(
        concept_text=concept_text, lineage_summary=lineage_summary,
    )

    if cache_system:
        system_payload: Any = [
            {"type": "text", "text": system_text,
             "cache_control": {"type": "ephemeral"}}
        ]
    else:
        system_payload = system_text

    request_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_payload,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": img_b64,
                }},
                {"type": "text", "text": user_text},
            ],
        }],
    }

    # 3. Make the call. SDK auto-retries 429 + 5xx (max_retries=2 default).
    try:
        client = llm._get_client()
        response = client.messages.create(**request_kwargs)
    except anthropic.AuthenticationError as e:
        _mark_call_failed(api_call_id, "auth_failed", str(e))
        raise VisionError(
            f"Anthropic auth failed: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=False,
        )
    except anthropic.RateLimitError as e:
        retry_after = (
            e.response.headers.get("retry-after") if e.response else None
        )
        _mark_call_failed(
            api_call_id, "rate_limited",
            f"{e}; retry_after={retry_after}",
        )
        raise VisionError(
            f"Anthropic rate limited (retry_after={retry_after}): {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=True,
        )
    except anthropic.APITimeoutError as e:
        _mark_call_failed(api_call_id, "timeout", str(e))
        raise VisionError(
            f"Anthropic timeout: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=True,
        )
    except anthropic.APIConnectionError as e:
        _mark_call_failed(api_call_id, "network_error", str(e))
        raise VisionError(
            f"Anthropic network error: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=True,
        )
    except anthropic.BadRequestError as e:
        # Failure mode 4.11: context window exceeded surfaces here for
        # vision (large lineage + image > 200K context). Distinguish from
        # other 400s by message inspection.
        msg = str(e).lower()
        is_context = "context" in msg or "too long" in msg or "exceed" in msg
        if is_context:
            _mark_call_failed(api_call_id, "context_exceeded", str(e))
            return VisionConsultationResponse(
                raw_response="", parsed=None, status="context_exceeded",
                cost_usd=0.0, tokens_input=0, tokens_output=0,
                used_downscale=used_downscale, api_call_id=api_call_id,
                model=model, failure_reason=f"context window exceeded: {e}",
            )
        _mark_call_failed(api_call_id, "bad_request", str(e))
        raise VisionError(
            f"Anthropic bad request: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=False,
        )
    except anthropic.APIStatusError as e:
        _mark_call_failed(api_call_id, "api_error", str(e))
        raise VisionError(
            f"Anthropic API error: {e}",
            api_call_id=api_call_id, sdk_error=e, retryable=True,
        )

    # 4. Extract text content. Vision response.content is a list of blocks;
    # we accumulate `text` blocks (ignore tool_use, etc.).
    text_content = ""
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text" or hasattr(block, "text"):
            text_content += getattr(block, "text", "")

    # 5. Cost + tokens. usage attribute names match Anthropic SDK.
    tokens_in = getattr(response.usage, "input_tokens", 0)
    tokens_out = getattr(response.usage, "output_tokens", 0)
    cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
    cost = llm.compute_cost(
        model, tokens_input=tokens_in, tokens_output=tokens_out,
        cache_read=cache_read, cache_creation=cache_creation,
    )

    # 6. Status discrimination.
    if detect_safety_refusal(text_content):
        status = "safety_refused"
        parsed = None
        failure_reason = "vision API content-policy refusal"
    else:
        parsed = parse_response_json(text_content)
        if parsed is None:
            status = "parse_failed"
            failure_reason = "could not extract JSON from response body"
        else:
            status = "completed"
            failure_reason = None

    # 7. Mark api_call succeeded (regardless of structure status — the
    # SDK call itself succeeded; status is about response interpretability).
    completed_iso = llm._iso_now()
    conn = db.connect()
    try:
        with conn:
            llm._update_api_call_succeeded(
                conn, api_call_id=api_call_id, completed=completed_iso,
                tokens_in=tokens_in, tokens_out=tokens_out, cost=cost,
            )
    finally:
        conn.close()

    return VisionConsultationResponse(
        raw_response=text_content,
        parsed=parsed,
        status=status,
        cost_usd=cost,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        used_downscale=used_downscale,
        api_call_id=api_call_id,
        model=model,
        failure_reason=failure_reason,
    )


def _mark_call_failed(api_call_id: str, status: str, error: str) -> None:
    completed = llm._iso_now()
    conn = db.connect()
    try:
        with conn:
            llm._update_api_call_failed(
                conn, api_call_id=api_call_id, completed=completed,
                status=status, error=error,
            )
    finally:
        conn.close()
