#!/usr/bin/env python3
"""Day 8 — failure modes 3b.1, 3b.2, 3b.4 (aging) + 3b.5 (inbox).

Tests:
  1. compute_attempt_age() at threshold boundaries
  2. awaiting_prompts() returns prompts with correct aging info
  3. manual_complete_attempt() flips attempt + prompt
  4. mark_attempt_failed() — solo case (prompt goes to failed)
  5. mark_attempt_failed() — multi-attempt case (prompt stays awaiting)
  6. kick_attempt() resets started
  7. inbox_renders() filters by router inbox path fragments

Cleans up via 'test_d8_' prefix on synthetic IDs.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
import dispatcher  # noqa: E402


def _assert(cond, msg):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def _iso(dt):
    return dt.isoformat()


def _insert_prompt(conn, pid, status="awaiting_return"):
    conn.execute(
        """
        INSERT INTO prompts (id, concept_id, tool, text_preview, status,
                             failure_reason, drafted_by, discipline_version,
                             yaml_path, created)
        VALUES (?, NULL, 'midjourney', 'test prompt', ?, NULL, 'manual',
                '1.0', '_test', ?)
        """,
        (pid, status, _iso(datetime.now(timezone.utc))),
    )


def _insert_attempt(conn, aid, prompt_id, attempt_number, started_iso,
                    status="in_flight"):
    conn.execute(
        """
        INSERT INTO generation_attempts (id, prompt_id, attempt_number,
                                          started, completed, status,
                                          trigger_method, notes)
        VALUES (?, ?, ?, ?, NULL, ?, 'clipboard_handoff', NULL)
        """,
        (aid, prompt_id, attempt_number, started_iso, status),
    )


def _insert_render(conn, rid, filepath):
    conn.execute(
        """
        INSERT INTO renders (id, attempt_id, prompt_id, filename, filepath,
                              download_hash, canonical_hash, tool, variant,
                              hero_status, discipline_version, yaml_path, created)
        VALUES (?, NULL, NULL, ?, ?, NULL, ?, 'midjourney', NULL, NULL,
                '1.0', '_test', ?)
        """,
        (rid, Path(filepath).name, filepath,
         "fake_canonical_hash_" + rid, _iso(datetime.now(timezone.utc))),
    )


def cleanup():
    db.cascading_delete("test_d8_")


def main() -> int:
    cleanup()  # idempotent: clear any leftover from a prior failed run
    now = datetime.now(timezone.utc)

    print("Test 1: compute_attempt_age boundaries")
    cases = [
        (now - timedelta(minutes=5),  "in_flight",  "in_flight"),
        (now - timedelta(minutes=29), "in_flight",  "in_flight"),
        (now - timedelta(minutes=30), "in_flight",  "still_waiting"),
        (now - timedelta(hours=2),    "in_flight",  "still_waiting"),
        (now - timedelta(hours=23, minutes=59), "in_flight",  "still_waiting"),
        (now - timedelta(hours=24),   "in_flight",  "stale_check"),
        (now - timedelta(hours=72),   "in_flight",  "stale_check"),
        (now - timedelta(minutes=5),  "completed",  "closed"),
        (now - timedelta(hours=24),   "failed",     "closed"),
    ]
    for started, status, expected in cases:
        age = dispatcher.compute_attempt_age(_iso(started), status, now=now)
        _assert(age["age_status"] == expected,
                f"started={started.isoformat()} status={status} "
                f"expected={expected} got={age['age_status']}")
    print(f"  9 boundary cases pass")

    print("\nTest 2: awaiting_prompts returns prompts with attempts + aging")
    conn = db.connect()
    try:
        with conn:
            _insert_prompt(conn, "test_d8_p1", status="awaiting_return")
            _insert_attempt(conn, "test_d8_a1", "test_d8_p1", 1,
                            _iso(now - timedelta(minutes=15)))
            _insert_attempt(conn, "test_d8_a2", "test_d8_p1", 2,
                            _iso(now - timedelta(hours=2)))
    finally:
        conn.close()

    awaiting = dispatcher.awaiting_prompts()
    matching = [p for p in awaiting if p["id"] == "test_d8_p1"]
    _assert(len(matching) == 1, f"expected 1 awaiting prompt, got {len(matching)}")
    p = matching[0]
    _assert(len(p["attempts"]) == 2, f"expected 2 attempts, got {len(p['attempts'])}")
    # attempts ordered by attempt_number DESC: #2 first, #1 second
    _assert(p["attempts"][0]["age_status"] == "still_waiting",
            f"attempt #2 (2h old) age: {p['attempts'][0]['age_status']}")
    _assert(p["attempts"][1]["age_status"] == "in_flight",
            f"attempt #1 (15min old) age: {p['attempts'][1]['age_status']}")
    print(f"  prompt with 2 attempts: in_flight + still_waiting verified")

    print("\nTest 3: manual_complete_attempt flips both")
    result = dispatcher.manual_complete_attempt("test_d8_a1", note="test note")
    _assert(result.get("ok"), f"manual_complete returned {result}")
    _assert(result["new_attempt_status"] == "completed", "attempt status")
    _assert(result["new_prompt_status"] == "completed", "prompt status")
    print(f"  attempt + prompt -> completed")

    print("\nTest 4: mark_attempt_failed — solo case (prompt -> failed)")
    conn = db.connect()
    try:
        with conn:
            _insert_prompt(conn, "test_d8_p2", status="awaiting_return")
            _insert_attempt(conn, "test_d8_a3", "test_d8_p2", 1,
                            _iso(now - timedelta(minutes=10)))
    finally:
        conn.close()

    result = dispatcher.mark_attempt_failed("test_d8_a3", "test failure reason")
    _assert(result.get("ok"), f"mark_failed returned {result}")
    _assert(result["new_prompt_status"] == "failed",
            f"solo failed should promote prompt to failed: {result['new_prompt_status']}")
    _assert(result["other_in_flight_attempts"] == 0,
            f"other_in_flight should be 0: {result['other_in_flight_attempts']}")
    print(f"  prompt -> failed (no other in-flight)")

    print("\nTest 5: mark_attempt_failed — multi-attempt (prompt stays awaiting)")
    conn = db.connect()
    try:
        with conn:
            _insert_prompt(conn, "test_d8_p3", status="awaiting_return")
            _insert_attempt(conn, "test_d8_a4", "test_d8_p3", 1,
                            _iso(now - timedelta(minutes=5)))
            _insert_attempt(conn, "test_d8_a5", "test_d8_p3", 2,
                            _iso(now - timedelta(minutes=2)))
    finally:
        conn.close()

    result = dispatcher.mark_attempt_failed("test_d8_a4", "first attempt timed out")
    _assert(result["new_prompt_status"] == "awaiting_return",
            f"prompt should stay awaiting (other in-flight): {result['new_prompt_status']}")
    _assert(result["other_in_flight_attempts"] == 1,
            f"other_in_flight should be 1: {result['other_in_flight_attempts']}")
    print(f"  prompt stays awaiting_return; 1 other in-flight remains")

    print("\nTest 6: kick_attempt resets started")
    # Read the second attempt's started time before
    conn = db.connect()
    try:
        before = conn.execute(
            "SELECT started FROM generation_attempts WHERE id='test_d8_a5'"
        ).fetchone()[0]
    finally:
        conn.close()

    result = dispatcher.kick_attempt("test_d8_a5")
    _assert(result.get("ok"), f"kick returned {result}")

    conn = db.connect()
    try:
        after = conn.execute(
            "SELECT started FROM generation_attempts WHERE id='test_d8_a5'"
        ).fetchone()[0]
    finally:
        conn.close()
    _assert(after != before, f"started should change after kick: before={before} after={after}")
    print(f"  started reset: {before[:19]} -> {after[:19]}")

    print("\nTest 7: inbox_renders filters by inbox path fragments")
    conn = db.connect()
    try:
        with conn:
            _insert_render(
                conn, "test_d8_r1",
                "projects/latent_systems/shared/visual_identity_phase1_references/_inbox/fake.png",
            )
            _insert_render(
                conn, "test_d8_r2",
                "projects/latent_systems/shared/visual_identity_phase1_references/_unclassified/fake2.png",
            )
            _insert_render(
                conn, "test_d8_r3",
                "projects/latent_systems/ep1/cold_open/sources/should_not_match.png",
            )
    finally:
        conn.close()

    inbox = dispatcher.inbox_renders()
    inbox_ids = {r["id"] for r in inbox}
    _assert("test_d8_r1" in inbox_ids, "_inbox/ render not found")
    _assert("test_d8_r2" in inbox_ids, "_unclassified/ render not found")
    _assert("test_d8_r3" not in inbox_ids,
            "non-inbox render incorrectly included")
    print(f"  inbox_renders found 2 expected, excluded 1 non-inbox")

    print("\nTest 8: cleanup")
    cleanup()
    awaiting = dispatcher.awaiting_prompts()
    _assert(not any(p["id"].startswith("test_d8_") for p in awaiting),
            "leftover test prompts after cleanup")
    print(f"  state.db clean of test_d8_ rows")

    print("\nPASS: all Day 8 failure-mode behaviors verified")
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_failure_modes.py`
    invocation remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
