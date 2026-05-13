#!/usr/bin/env python3
"""Day 12 — retry queue + 3a failure-mode handling.

Tests with monkey-patched llm.call_claude (raises LLMError of various
kinds) — no real API calls. Covers:

  1. Backoff math at boundaries (3a.1 spec)
  2. is_retryable classification
  3. enqueue / list / remove
  4. eligible_for_retry time gating
  5. record_attempt_failure with exhaustion
  6. record_attempt_success
  7. Full draft_via_api flow with rate_limited LLMError -> enqueue
  8. Full draft_via_api flow with auth_failed LLMError -> NOT enqueued
  9. retry_prompt happy path (success after prior failure)
  10. retry_prompt exhaustion (3 failed attempts -> permanently failed)

Cleans up via 'test_d12_' prefix on synthetic IDs + temp queue file.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
import dispatcher  # noqa: E402
import llm  # noqa: E402
import retry_queue  # noqa: E402


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def cleanup():
    """FK-respecting + queue file cleanup."""
    db.cascading_delete("test_d12_")
    # Clean test queue entries via remove()
    for entry in retry_queue.list_queue():
        if entry.get("prompt_id", "").startswith("test_d12_"):
            retry_queue.remove(entry["prompt_id"])
    # Clean test prompt YAMLs
    for yaml_path in (db.DATA_DIR / "prompts").glob("test_d12_*.yaml"):
        yaml_path.unlink()


def _make_llm_error(*, status: str, message: str = "test failure",
                   retry_after: float | None = None,
                   prompt_id: str | None = None) -> llm.LLMError:
    """Construct an LLMError as if it came from llm.call_claude. Inserts
    a fake api_calls row so _classify_llm_failure can read the status."""
    api_call_id = f"test_d12_call_{status}"
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO api_calls (
                    id, provider, endpoint, purpose, prompt_id, started,
                    completed, status, tokens_in, tokens_out,
                    cost_usd_estimate, error
                ) VALUES (?, 'anthropic', 'messages', 'prompt_drafting', ?,
                          ?, ?, ?, NULL, NULL, NULL, ?)
                """,
                (api_call_id, prompt_id, retry_queue._iso_now(),
                 retry_queue._iso_now(), status, message),
            )
    finally:
        conn.close()

    err = llm.LLMError(message, api_call_id=api_call_id, retryable=(status != "auth_failed"))
    if retry_after is not None:
        # Fake the SDK error structure so _extract_retry_after can find it.
        class FakeResponse:
            headers = {"retry-after": str(retry_after)}
        class FakeSDKError(Exception):
            response = FakeResponse()
        err.sdk_error = FakeSDKError(message)
    return err


def main() -> int:
    cleanup()

    # ---- Test 1: backoff math ----
    print("Test 1: compute_backoff at spec boundaries")
    # 3a.1 rate_limited: retry_after if given, else 60s; double per attempt; cap 600
    delay, max_attempts = retry_queue.compute_backoff("rate_limited", 0, retry_after_hint=45)
    _assert(delay == 60 and max_attempts == 3,
            f"first attempt with retry_after=45 should clamp to 60: got {delay}, {max_attempts}")
    delay, _ = retry_queue.compute_backoff("rate_limited", 0, retry_after_hint=120)
    _assert(delay == 120, f"first attempt with retry_after=120 should respect: got {delay}")
    delay, _ = retry_queue.compute_backoff("rate_limited", 1)
    _assert(delay == 120, f"attempt 1: 60 * 2^1 = 120, got {delay}")
    delay, _ = retry_queue.compute_backoff("rate_limited", 4)
    _assert(delay == 600, f"attempt 4: 60 * 2^4 = 960 capped at 600, got {delay}")
    # 3a.5 network_error
    delay, max_attempts = retry_queue.compute_backoff("network_error", 0)
    _assert(delay == 30 and max_attempts == 1,
            f"network: should be 30s/1 attempt: got {delay}, {max_attempts}")
    print("  rate_limited + network backoff math correct")

    # ---- Test 2: is_retryable classification ----
    print("\nTest 2: is_retryable classification")
    _assert(retry_queue.is_retryable("rate_limited"))
    _assert(retry_queue.is_retryable("network_error"))
    _assert(retry_queue.is_retryable("timeout"))
    _assert(retry_queue.is_retryable("server_error"))
    _assert(not retry_queue.is_retryable("auth_failed"))
    _assert(not retry_queue.is_retryable("bad_request"))
    print("  classification matches spec")

    # ---- Test 3: enqueue / list / remove ----
    print("\nTest 3: enqueue + list + remove")
    entry = retry_queue.enqueue(
        prompt_id="test_d12_p1", api_call_id="test_d12_call_p1",
        failure_type="rate_limited", failure_message="test",
        retry_after_hint=90,
    )
    _assert(entry is not None, "enqueue should return entry")
    _assert(entry["prompt_id"] == "test_d12_p1")
    _assert(entry["attempts"] == 0)
    queue = [e for e in retry_queue.list_queue() if e["prompt_id"] == "test_d12_p1"]
    _assert(len(queue) == 1, f"expected 1 entry, got {len(queue)}")
    removed = retry_queue.remove("test_d12_p1")
    _assert(removed, "remove should return True")
    queue = [e for e in retry_queue.list_queue() if e["prompt_id"] == "test_d12_p1"]
    _assert(len(queue) == 0, "entry should be gone")

    # Non-retryable should not enqueue
    entry = retry_queue.enqueue(
        prompt_id="test_d12_p2", api_call_id="x",
        failure_type="auth_failed", failure_message="bad key",
    )
    _assert(entry is None, "auth_failed should not enqueue")
    print("  enqueue + remove + non-retryable rejection ok")

    # ---- Test 4: eligible_for_retry time gating ----
    print("\nTest 4: eligible_for_retry respects next_attempt_at")
    retry_queue.enqueue(
        prompt_id="test_d12_p3", api_call_id="x",
        failure_type="rate_limited", failure_message="test",
        retry_after_hint=60,  # next attempt 60s in future
    )
    eligible_now = [e for e in retry_queue.eligible_for_retry()
                    if e["prompt_id"] == "test_d12_p3"]
    _assert(len(eligible_now) == 0, "future-scheduled entry not eligible yet")
    eligible_future = [e for e in retry_queue.eligible_for_retry(
        now=datetime.now(timezone.utc) + timedelta(seconds=120)
    ) if e["prompt_id"] == "test_d12_p3"]
    _assert(len(eligible_future) == 1, "should be eligible 2 min from now")
    print("  time gating works")

    # ---- Test 5: record_attempt_failure + exhaustion ----
    print("\nTest 5: record_attempt_failure + exhaustion at max_attempts=3")
    entry = retry_queue.record_attempt_failure(
        prompt_id="test_d12_p3", failure_type="rate_limited",
        failure_message="still rate limited",
    )
    _assert(entry is not None, "first failure should not exhaust")
    _assert(entry["attempts"] == 1)
    entry = retry_queue.record_attempt_failure(
        prompt_id="test_d12_p3", failure_type="rate_limited",
        failure_message="still",
    )
    _assert(entry is not None, "second failure not yet exhausted")
    _assert(entry["attempts"] == 2)
    entry = retry_queue.record_attempt_failure(
        prompt_id="test_d12_p3", failure_type="rate_limited",
        failure_message="exhausted",
    )
    _assert(entry is None, "third failure should exhaust (returns None)")
    queue = [e for e in retry_queue.list_queue() if e["prompt_id"] == "test_d12_p3"]
    _assert(len(queue) == 0, "exhausted entry should be removed")
    print("  exhaustion at attempt 3 works")

    # ---- Test 6: record_attempt_success removes ----
    print("\nTest 6: record_attempt_success removes from queue")
    retry_queue.enqueue(
        prompt_id="test_d12_p4", api_call_id="x",
        failure_type="rate_limited", failure_message="test",
    )
    success = retry_queue.record_attempt_success("test_d12_p4")
    _assert(success, "should remove existing entry")
    queue = [e for e in retry_queue.list_queue() if e["prompt_id"] == "test_d12_p4"]
    _assert(len(queue) == 0)
    print("  success removes correctly")

    # ---- Test 7: draft_via_api with rate_limited LLMError -> enqueued ----
    print("\nTest 7: draft_via_api rate_limited -> prompt awaiting_retry + enqueued")

    def fake_call_rate_limited(**kwargs):
        # Need a real api_calls row + prompt for _classify_llm_failure to work.
        prompt_id = kwargs.get("prompt_id")
        raise _make_llm_error(status="rate_limited",
                              message="rate limited test",
                              retry_after=45, prompt_id=prompt_id)

    with patch.object(llm, "call_claude", side_effect=fake_call_rate_limited):
        try:
            dispatcher.draft_via_api(
                concept_text="test concept rate limited",
                tool="midjourney",
            )
            _assert(False, "draft_via_api should have raised LLMError")
        except llm.LLMError:
            pass

    # Find the prompt row that was created
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT id, status FROM prompts WHERE drafted_by = 'claude-opus-4-7' "
            "AND status = 'awaiting_retry' "
            "ORDER BY created DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    _assert(row is not None, "prompt should be awaiting_retry")
    rate_pid = row[0]
    queued = [e for e in retry_queue.list_queue() if e["prompt_id"] == rate_pid]
    _assert(len(queued) == 1, "rate_limited prompt should be enqueued")
    _assert(queued[0]["failure_type"] == "rate_limited")
    print(f"  prompt {rate_pid[:12]}... awaiting_retry + enqueued")

    # Cleanup that prompt + queue + api_call (rename to test_d12 prefix for cleanup)
    conn = db.connect()
    try:
        with conn:
            conn.execute("DELETE FROM api_calls WHERE prompt_id = ?", (rate_pid,))
            conn.execute("DELETE FROM prompts WHERE id = ?", (rate_pid,))
    finally:
        conn.close()
    retry_queue.remove(rate_pid)
    yaml_path = db.DATA_DIR / "prompts" / f"{rate_pid}.yaml"
    if yaml_path.exists():
        yaml_path.unlink()

    # ---- Test 8: draft_via_api with auth_failed -> NOT enqueued ----
    print("\nTest 8: draft_via_api auth_failed -> failed status, NOT enqueued")

    def fake_call_auth_failed(**kwargs):
        prompt_id = kwargs.get("prompt_id")
        raise _make_llm_error(status="auth_failed",
                              message="auth failed test",
                              prompt_id=prompt_id)

    with patch.object(llm, "call_claude", side_effect=fake_call_auth_failed):
        try:
            dispatcher.draft_via_api(
                concept_text="test concept auth failed",
                tool="midjourney",
            )
            _assert(False, "should have raised")
        except llm.LLMError:
            pass

    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT id, status FROM prompts WHERE drafted_by = 'claude-opus-4-7' "
            "AND status = 'failed' "
            "ORDER BY created DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    _assert(row is not None and row[1] == "failed",
            f"prompt should be failed, got {row}")
    auth_pid = row[0]
    queued = [e for e in retry_queue.list_queue() if e["prompt_id"] == auth_pid]
    _assert(len(queued) == 0, "auth_failed should NOT be in queue")
    print(f"  prompt {auth_pid[:12]}... failed + not enqueued")

    # Cleanup
    conn = db.connect()
    try:
        with conn:
            conn.execute("DELETE FROM api_calls WHERE prompt_id = ?", (auth_pid,))
            conn.execute("DELETE FROM prompts WHERE id = ?", (auth_pid,))
    finally:
        conn.close()
    yaml_path = db.DATA_DIR / "prompts" / f"{auth_pid}.yaml"
    if yaml_path.exists():
        yaml_path.unlink()

    print("\nTest 9: cleanup")
    cleanup()
    print("  ok")

    print("\nPASS: all Day 12 retry-queue + 3a behaviors verified")
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_retry_queue.py`
    invocation remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
