#!/usr/bin/env python3
"""Phase 2 Wave B — Anthropic vision adapter tests.

Two test surfaces:
  1. Pure helpers (build_system_prompt, build_user_message,
     encode_image_b64, parse_response_json, detect_safety_refusal) —
     no SDK mocking, no state.db touch.
  2. call_vision orchestrator with mocked llm._get_client to bypass
     the real Anthropic API. Covers happy path + parse_failed +
     safety_refused + context_exceeded + SDK exceptions (rate limit,
     auth, timeout, bad request).

Test data: synthetic PNGs under _data/_test_vision/ (gitignored).
api_calls cleanup correlates by id collected from response objects.

Run: python tool_build/tests/test_vision_anthropic.py
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (Pattern #3: import db for codec setup)
import llm  # noqa: E402
from audit_providers import anthropic as vision  # noqa: E402


TEST_DIR = db.DATA_DIR / "_test_vision"
TRACKED_CALL_IDS: list[str] = []


SAMPLE_RUBRIC = {
    "version": "1.0",
    "discipline_version": "1.0",
    "applies_to_concept_types": ["schematic_apparatus"],
    "criteria": {
        "Composition": {
            "definition": "The framing of the render — placement and relationships.",
            "pass": "composition reads at-a-glance",
            "partial": "composition coherent but requires study",
            "fail": "composition incoherent",
        },
        "Register coherence": {
            "definition": "Tonal/period vocabulary holds across the frame.",
            "pass": "register holds at 100%",
            "partial": "register mostly holds",
            "fail": "register breaks",
        },
    },
}


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def cleanup():
    """Delete tracked api_calls rows + test scratch files."""
    if TRACKED_CALL_IDS:
        conn = db.connect()
        try:
            with conn:
                placeholders = ",".join("?" for _ in TRACKED_CALL_IDS)
                conn.execute(
                    f"DELETE FROM api_calls WHERE id IN ({placeholders})",
                    TRACKED_CALL_IDS,
                )
        finally:
            conn.close()
        TRACKED_CALL_IDS.clear()
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR, ignore_errors=True)


def _make_test_png() -> Path:
    """Synthetic small PNG for image-encoding tests."""
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    p = TEST_DIR / "fixture.png"
    Image.new("RGB", (64, 64), color=(180, 80, 40)).save(p, format="PNG")
    return p


# ----------------------------------------------------------------------
# Pure-helper tests
# ----------------------------------------------------------------------

def test_build_system_prompt_with_criteria():
    sys_prompt = vision.build_system_prompt(SAMPLE_RUBRIC)
    _assert("verdict_inference" in sys_prompt)
    _assert("hero_zone" in sys_prompt and "reject" in sys_prompt)
    _assert("Rubric version 1.0" in sys_prompt)
    _assert("### Composition" in sys_prompt)
    _assert("### Register coherence" in sys_prompt)
    _assert("- pass: composition reads at-a-glance" in sys_prompt)


def test_build_system_prompt_no_criteria():
    rubric_empty = {
        "version": "1.0", "discipline_version": "1.0",
        "applies_to_concept_types": [], "criteria": {},
    }
    sys_prompt = vision.build_system_prompt(rubric_empty)
    _assert("No criteria defined" in sys_prompt)


def test_build_user_message_concept_only():
    msg = vision.build_user_message(concept_text="rat at slot machine")
    _assert("Concept context:" in msg)
    _assert("rat at slot machine" in msg)
    _assert("Lineage chain:" not in msg)
    _assert("Evaluate the attached image" in msg)


def test_build_user_message_with_lineage():
    msg = vision.build_user_message(
        concept_text="concept text",
        lineage_summary="render r1 -> render r2 -> this render",
    )
    _assert("Concept context:" in msg)
    _assert("Lineage chain:" in msg)


def test_build_user_message_minimal():
    msg = vision.build_user_message()
    _assert("Evaluate the attached image" in msg)
    # No prefix sections when neither argument provided
    _assert("Concept context:" not in msg)
    _assert("Lineage chain:" not in msg)


def test_encode_image_b64_png():
    p = _make_test_png()
    data, media_type = vision.encode_image_b64(p)
    _assert(media_type == "image/png")
    _assert(len(data) > 100)  # non-trivial base64
    # Round-trip: decode and confirm it's a valid PNG header
    import base64
    raw = base64.standard_b64decode(data)
    _assert(raw[:8] == b"\x89PNG\r\n\x1a\n", "decoded bytes should be PNG signature")


def test_encode_image_b64_unsupported_extension():
    p = TEST_DIR / "fixture.bmp"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"BMx\x00\x00\x00")  # garbage; won't be opened
    try:
        vision.encode_image_b64(p)
    except ValueError as e:
        _assert("unsupported" in str(e).lower())
        return
    _assert(False, "expected ValueError on unsupported format")


def test_encode_image_b64_missing_file():
    try:
        vision.encode_image_b64(TEST_DIR / "ghost.png")
    except FileNotFoundError:
        return
    _assert(False, "expected FileNotFoundError")


def test_parse_response_json_direct():
    text = '{"verdict_inference": "strong", "criteria_match": {"Composition": "pass"}}'
    parsed = vision.parse_response_json(text)
    _assert(parsed is not None)
    _assert(parsed["verdict_inference"] == "strong")


def test_parse_response_json_in_prose():
    text = '''Here is my evaluation.

{"verdict_inference": "weak", "key_observations": ["x", "y"]}

Hope this helps.'''
    parsed = vision.parse_response_json(text)
    _assert(parsed is not None)
    _assert(parsed["verdict_inference"] == "weak")
    _assert(len(parsed["key_observations"]) == 2)


def test_parse_response_json_invalid():
    _assert(vision.parse_response_json("just prose, no json") is None)
    _assert(vision.parse_response_json("") is None)
    _assert(vision.parse_response_json("{ broken json [") is None)


def test_parse_response_json_array_returns_none():
    """Arrays at the top level aren't valid response shape; None."""
    _assert(vision.parse_response_json('["just", "an", "array"]') is None)


def test_detect_safety_refusal_positive():
    refusal_texts = [
        "I can't evaluate this image as it depicts...",
        "I cannot help with this request because of safety concerns.",
        "I'm not able to process this image due to content policy.",
        "Unable to assist with this evaluation.",
    ]
    for t in refusal_texts:
        _assert(vision.detect_safety_refusal(t),
                f"should detect refusal in: {t[:60]}...")


def test_detect_safety_refusal_negative():
    """Critical evaluations are not refusals — must distinguish."""
    legit_critical = [
        "Composition is incoherent. The subject is unclear.",
        '{"verdict_inference": "fail", "criteria_match": {"Composition": "fail"}}',
        "The render fails on register coherence; mixed-period elements present.",
    ]
    for t in legit_critical:
        _assert(not vision.detect_safety_refusal(t),
                f"should NOT detect refusal in legitimate evaluation: {t[:60]}")


def test_detect_safety_refusal_empty():
    _assert(not vision.detect_safety_refusal(""))


# ----------------------------------------------------------------------
# Orchestrator tests with mocked SDK
# ----------------------------------------------------------------------

def _fake_response(text: str, in_tokens: int = 1500, out_tokens: int = 200):
    """Fake an Anthropic Message response with text content + usage."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    resp.usage = MagicMock()
    resp.usage.input_tokens = in_tokens
    resp.usage.output_tokens = out_tokens
    resp.usage.cache_read_input_tokens = 0
    resp.usage.cache_creation_input_tokens = 0
    return resp


def _mocked_client(*, return_value=None, side_effect=None):
    client = MagicMock()
    client.messages = MagicMock()
    if side_effect is not None:
        client.messages.create = MagicMock(side_effect=side_effect)
    else:
        client.messages.create = MagicMock(return_value=return_value)
    return client


def test_call_vision_completed():
    p = _make_test_png()
    json_response = (
        '{"verdict_inference": "strong", '
        '"criteria_match": {"Composition": "pass", "Register coherence": "partial"}, '
        '"key_observations": ["clean foreground", "register holds"]}'
    )
    fake_resp = _fake_response(json_response, in_tokens=2200, out_tokens=85)
    client = _mocked_client(return_value=fake_resp)

    with patch.object(llm, "_get_client", return_value=client):
        result = vision.call_vision(image_path=p, rubric=SAMPLE_RUBRIC)
    TRACKED_CALL_IDS.append(result.api_call_id)

    _assert(result.status == "completed", f"expected completed, got {result.status}")
    _assert(result.parsed is not None)
    _assert(result.parsed["verdict_inference"] == "strong")
    _assert(result.tokens_input == 2200)
    _assert(result.tokens_output == 85)
    _assert(result.cost_usd > 0)
    _assert(result.failure_reason is None)


def test_call_vision_parse_failed():
    p = _make_test_png()
    fake_resp = _fake_response(
        "Hmm, I see a render but cannot return JSON for some reason."
    )
    client = _mocked_client(return_value=fake_resp)
    with patch.object(llm, "_get_client", return_value=client):
        result = vision.call_vision(image_path=p, rubric=SAMPLE_RUBRIC)
    TRACKED_CALL_IDS.append(result.api_call_id)
    _assert(result.status == "parse_failed")
    _assert(result.parsed is None)
    _assert("could not extract" in (result.failure_reason or "").lower())


def test_call_vision_safety_refused():
    p = _make_test_png()
    fake_resp = _fake_response(
        "I can't evaluate this image due to safety guidelines around content depicted."
    )
    client = _mocked_client(return_value=fake_resp)
    with patch.object(llm, "_get_client", return_value=client):
        result = vision.call_vision(image_path=p, rubric=SAMPLE_RUBRIC)
    TRACKED_CALL_IDS.append(result.api_call_id)
    _assert(result.status == "safety_refused",
            f"expected safety_refused, got {result.status}")
    _assert(result.parsed is None)
    _assert("policy" in (result.failure_reason or "").lower())


def test_call_vision_context_exceeded():
    """BadRequestError with 'context' in message -> status=context_exceeded
    (returned, not raised). Other BadRequestErrors raise VisionError."""
    p = _make_test_png()
    err = anthropic.BadRequestError(
        message="prompt is too long: context window of 200000 tokens exceeded",
        response=MagicMock(status_code=400),
        body={},
    )
    client = _mocked_client(side_effect=err)
    with patch.object(llm, "_get_client", return_value=client):
        result = vision.call_vision(image_path=p, rubric=SAMPLE_RUBRIC)
    TRACKED_CALL_IDS.append(result.api_call_id)
    _assert(result.status == "context_exceeded")
    _assert("context window exceeded" in (result.failure_reason or "").lower())
    _assert(result.tokens_input == 0)  # no usage data when error pre-empted


def test_call_vision_rate_limit_raises():
    p = _make_test_png()
    response_mock = MagicMock()
    response_mock.headers = {"retry-after": "60"}
    err = anthropic.RateLimitError(
        message="rate limited",
        response=response_mock, body={},
    )
    client = _mocked_client(side_effect=err)
    with patch.object(llm, "_get_client", return_value=client):
        try:
            result = vision.call_vision(image_path=p, rubric=SAMPLE_RUBRIC)
            TRACKED_CALL_IDS.append(result.api_call_id)
            _assert(False, "expected VisionError on rate limit")
        except vision.VisionError as e:
            TRACKED_CALL_IDS.append(e.api_call_id)
            _assert(e.retryable is True, "rate limit must be retryable")


def test_call_vision_auth_error_raises():
    p = _make_test_png()
    err = anthropic.AuthenticationError(
        message="invalid api key",
        response=MagicMock(status_code=401), body={},
    )
    client = _mocked_client(side_effect=err)
    with patch.object(llm, "_get_client", return_value=client):
        try:
            result = vision.call_vision(image_path=p, rubric=SAMPLE_RUBRIC)
            TRACKED_CALL_IDS.append(result.api_call_id)
            _assert(False, "expected VisionError on auth")
        except vision.VisionError as e:
            TRACKED_CALL_IDS.append(e.api_call_id)
            _assert(e.retryable is False, "auth must NOT be retryable")


def test_call_vision_bad_request_other_raises():
    """BadRequestError without 'context' marker -> raise VisionError(retryable=False)."""
    p = _make_test_png()
    err = anthropic.BadRequestError(
        message="invalid model name",
        response=MagicMock(status_code=400), body={},
    )
    client = _mocked_client(side_effect=err)
    with patch.object(llm, "_get_client", return_value=client):
        try:
            result = vision.call_vision(image_path=p, rubric=SAMPLE_RUBRIC)
            TRACKED_CALL_IDS.append(result.api_call_id)
            _assert(False, "expected VisionError on non-context bad request")
        except vision.VisionError as e:
            TRACKED_CALL_IDS.append(e.api_call_id)
            _assert(e.retryable is False)


def main():
    cleanup()
    try:
        # Pure helpers
        test_build_system_prompt_with_criteria()
        test_build_system_prompt_no_criteria()
        test_build_user_message_concept_only()
        test_build_user_message_with_lineage()
        test_build_user_message_minimal()
        test_encode_image_b64_png()
        test_encode_image_b64_unsupported_extension()
        test_encode_image_b64_missing_file()
        test_parse_response_json_direct()
        test_parse_response_json_in_prose()
        test_parse_response_json_invalid()
        test_parse_response_json_array_returns_none()
        test_detect_safety_refusal_positive()
        test_detect_safety_refusal_negative()
        test_detect_safety_refusal_empty()
        # Orchestrator
        test_call_vision_completed()
        test_call_vision_parse_failed()
        test_call_vision_safety_refused()
        test_call_vision_context_exceeded()
        test_call_vision_rate_limit_raises()
        test_call_vision_auth_error_raises()
        test_call_vision_bad_request_other_raises()
    finally:
        cleanup()
    print("PASS: vision adapter — pure helpers + orchestrator paths "
          "(completed / parse_failed / safety_refused / context_exceeded / "
          "rate_limit / auth / bad_request)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
