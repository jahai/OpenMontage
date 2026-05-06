#!/usr/bin/env python3
"""Day 9 — render-attempt-prompt binding (Feature 3b loop close).

Tests the full decision matrix:
  1. Auto-bind: 1 in_flight + matching tool -> bind succeeds
  2. Tool-mismatch (3b.3): 1 in_flight + tool diff -> needs_review_reason
  3. Multiple open (3b.6): 2+ in_flight -> needs_review_reason
  4. Orphan: 0 in_flight -> needs_review_reason='orphan'
  5. Manual bind without force on mismatch -> refused
  6. Manual bind with force=True on mismatch -> bound (3b.3 'bind anyway')
  7. mark_render_orphan stamps YAML
  8. Re-bind refused on already-bound render

Cleans up via 'test_d9_' prefix on synthetic IDs + matching YAML files.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
import dispatcher  # noqa: E402
import yaml as _yaml  # noqa: E402


def _assert(cond, msg):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def _iso(dt):
    return dt.isoformat()


def _now():
    return datetime.now(timezone.utc)


def _ins_prompt(conn, pid, tool="midjourney", status="awaiting_return"):
    conn.execute(
        """
        INSERT INTO prompts (id, concept_id, tool, text_preview, status,
                             failure_reason, drafted_by, discipline_version,
                             yaml_path, created)
        VALUES (?, NULL, ?, 'test', ?, NULL, 'manual', '1.0', '_test', ?)
        """,
        (pid, tool, status, _iso(_now())),
    )


def _ins_attempt(conn, aid, prompt_id, n=1, status="in_flight"):
    conn.execute(
        """
        INSERT INTO generation_attempts (id, prompt_id, attempt_number, started,
                                          completed, status, trigger_method, notes)
        VALUES (?, ?, ?, ?, NULL, ?, 'clipboard_handoff', NULL)
        """,
        (aid, prompt_id, n, _iso(_now()), status),
    )


def _ins_render(conn, rid, tool="midjourney"):
    """Insert a render row + matching YAML file (auto_bind reads/writes YAMLs)."""
    conn.execute(
        """
        INSERT INTO renders (id, attempt_id, prompt_id, filename, filepath,
                              download_hash, canonical_hash, tool, variant,
                              hero_status, discipline_version, yaml_path, created)
        VALUES (?, NULL, NULL, ?, ?, NULL, ?, ?, NULL, NULL, '1.0',
                ?, ?)
        """,
        (rid, f"{rid}.png", f"projects/latent_systems/_test/{rid}.png",
         "fake_canonical_hash_" + rid, tool,
         f"projects/latent_systems/tool_build/_data/renders/{rid}.yaml",
         _iso(_now())),
    )
    # Seed the YAML file so _update_render_yaml has something to patch.
    yaml_abs = db.DATA_DIR / "renders" / f"{rid}.yaml"
    yaml_abs.parent.mkdir(parents=True, exist_ok=True)
    with yaml_abs.open("w", encoding="utf-8") as f:
        _yaml.safe_dump({"id": rid, "tool": tool, "discipline_version": "1.0"},
                        f, sort_keys=False)


def _read_yaml(rid):
    yaml_abs = db.DATA_DIR / "renders" / f"{rid}.yaml"
    if not yaml_abs.exists():
        return None
    return _yaml.safe_load(yaml_abs.read_text(encoding="utf-8"))


def cleanup():
    """db.cascading_delete walks the FK graph child-first. See db.py
    _CASCADE_DELETE_ORDER for the table sequence."""
    db.cascading_delete("test_d9_")
    # Delete test YAMLs.
    for yaml_path in (db.DATA_DIR / "renders").glob("test_d9_*.yaml"):
        yaml_path.unlink()


def main() -> int:
    cleanup()  # idempotent

    # ---- Test 1: auto-bind happy path (1 in_flight + tool match) ----
    print("Test 1: auto-bind on single matching attempt")
    conn = db.connect()
    try:
        with conn:
            _ins_prompt(conn, "test_d9_p1", tool="midjourney")
            _ins_attempt(conn, "test_d9_a1", "test_d9_p1")
            _ins_render(conn, "test_d9_r1", tool="midjourney")
    finally:
        conn.close()

    result = dispatcher.auto_bind_render("test_d9_r1")
    _assert(result["decision"] == "auto_bound",
            f"expected auto_bound, got {result['decision']}")
    _assert(result["ok"], f"auto-bind failed: {result}")

    # Verify DB state
    conn = db.connect()
    try:
        r = conn.execute("SELECT attempt_id, prompt_id FROM renders WHERE id='test_d9_r1'").fetchone()
        _assert(r[0] == "test_d9_a1", f"render.attempt_id: {r[0]}")
        _assert(r[1] == "test_d9_p1", f"render.prompt_id: {r[1]}")
        a = conn.execute("SELECT status FROM generation_attempts WHERE id='test_d9_a1'").fetchone()
        _assert(a[0] == "completed", f"attempt status: {a[0]}")
        p = conn.execute("SELECT status FROM prompts WHERE id='test_d9_p1'").fetchone()
        _assert(p[0] == "completed", f"prompt status: {p[0]}")
    finally:
        conn.close()

    yaml_data = _read_yaml("test_d9_r1")
    _assert(yaml_data["attempt_id"] == "test_d9_a1", "yaml attempt_id")
    _assert(yaml_data["binding"]["method"] == "tool_match", "yaml binding method")
    print("  bound; attempt+prompt completed; yaml stamped")

    # ---- Test 2: tool mismatch (3b.3) ----
    print("\nTest 2: tool mismatch -> no auto-bind, needs_review_reason set")
    conn = db.connect()
    try:
        with conn:
            _ins_prompt(conn, "test_d9_p2", tool="kling")  # kling prompt
            _ins_attempt(conn, "test_d9_a2", "test_d9_p2")
            _ins_render(conn, "test_d9_r2", tool="midjourney")  # MJ render
    finally:
        conn.close()

    result = dispatcher.auto_bind_render("test_d9_r2")
    _assert(result["decision"] == "tool_mismatch",
            f"expected tool_mismatch, got {result['decision']}")

    yaml_data = _read_yaml("test_d9_r2")
    _assert(yaml_data["needs_review_reason"] == "tool_mismatch", "yaml reason")
    _assert(yaml_data["candidate_attempt_id"] == "test_d9_a2", "yaml candidate")

    conn = db.connect()
    try:
        r = conn.execute("SELECT attempt_id FROM renders WHERE id='test_d9_r2'").fetchone()
        _assert(r[0] is None, f"render should not be bound: attempt_id={r[0]}")
    finally:
        conn.close()
    print("  not bound; reason=tool_mismatch; candidate hint stamped")

    # ---- Test 3: multiple open attempts (3b.6) ----
    print("\nTest 3: 2+ open attempts -> needs_review_reason='multiple_open_attempts'")
    conn = db.connect()
    try:
        with conn:
            _ins_prompt(conn, "test_d9_p3a", tool="midjourney")
            _ins_attempt(conn, "test_d9_a3a", "test_d9_p3a", n=1)
            _ins_prompt(conn, "test_d9_p3b", tool="midjourney")
            _ins_attempt(conn, "test_d9_a3b", "test_d9_p3b", n=1)
            _ins_render(conn, "test_d9_r3", tool="midjourney")
    finally:
        conn.close()

    result = dispatcher.auto_bind_render("test_d9_r3")
    _assert(result["decision"] == "multiple_open_attempts",
            f"expected multiple_open_attempts, got {result['decision']}")
    _assert(result["open_attempt_count"] >= 2, f"open count: {result['open_attempt_count']}")

    yaml_data = _read_yaml("test_d9_r3")
    _assert(yaml_data["needs_review_reason"] == "multiple_open_attempts", "yaml reason")
    print(f"  not bound; reason=multiple_open_attempts; default candidate captured")

    # ---- Test 4: orphan (0 in_flight) ----
    print("\nTest 4: 0 open attempts -> orphan")
    # First close all in_flight attempts so orphan check works.
    conn = db.connect()
    try:
        with conn:
            conn.execute("UPDATE generation_attempts SET status='completed' WHERE id LIKE 'test_d9_%'")
            _ins_render(conn, "test_d9_r4", tool="midjourney")
    finally:
        conn.close()

    result = dispatcher.auto_bind_render("test_d9_r4")
    _assert(result["decision"] == "orphan", f"expected orphan, got {result['decision']}")
    yaml_data = _read_yaml("test_d9_r4")
    _assert(yaml_data["needs_review_reason"] == "orphan", "yaml reason")
    print("  reason=orphan stamped")

    # ---- Test 5: manual bind without force on mismatch -> refused ----
    print("\nTest 5: bind_render_to_attempt refuses mismatch without force")
    conn = db.connect()
    try:
        with conn:
            _ins_prompt(conn, "test_d9_p5", tool="kling")
            _ins_attempt(conn, "test_d9_a5", "test_d9_p5")
            _ins_render(conn, "test_d9_r5", tool="midjourney")
    finally:
        conn.close()

    result = dispatcher.bind_render_to_attempt("test_d9_r5", "test_d9_a5", force=False)
    _assert(not result["ok"], f"expected refusal, got {result}")
    _assert(result["error"] == "tool_mismatch", f"expected tool_mismatch error: {result}")
    print("  refused with tool_mismatch error")

    # ---- Test 6: manual bind with force=True succeeds (3b.3 'bind anyway') ----
    print("\nTest 6: bind_render_to_attempt force=True bypasses mismatch")
    result = dispatcher.bind_render_to_attempt("test_d9_r5", "test_d9_a5", force=True)
    _assert(result["ok"], f"force-bind failed: {result}")
    _assert(not result["tool_match"], "tool_match should be False")
    _assert(result["force"], "force flag should be True")

    yaml_data = _read_yaml("test_d9_r5")
    _assert(yaml_data["binding"]["method"] == "force", "yaml method")
    _assert(yaml_data["binding"]["tool_mismatch_overridden"] is True, "yaml override flag")
    print("  bound; method=force; override flag set")

    # ---- Test 7: mark_render_orphan ----
    print("\nTest 7: mark_render_orphan stamps YAML")
    conn = db.connect()
    try:
        with conn:
            _ins_render(conn, "test_d9_r7", tool="midjourney")
    finally:
        conn.close()

    result = dispatcher.mark_render_orphan("test_d9_r7", note="confirmed not from v1")
    _assert(result["ok"], "mark_render_orphan failed")
    yaml_data = _read_yaml("test_d9_r7")
    _assert(yaml_data["needs_review_reason"] == "orphan_confirmed", "yaml reason")
    _assert(yaml_data["orphan_confirmed_note"] == "confirmed not from v1", "yaml note")
    print("  reason=orphan_confirmed stamped with note")

    # ---- Test 8: re-bind refused ----
    print("\nTest 8: re-bind refused on already-bound render")
    # test_d9_r1 was bound in Test 1.
    conn = db.connect()
    try:
        with conn:
            _ins_prompt(conn, "test_d9_p8", tool="midjourney")
            _ins_attempt(conn, "test_d9_a8", "test_d9_p8")
    finally:
        conn.close()

    result = dispatcher.bind_render_to_attempt("test_d9_r1", "test_d9_a8")
    _assert(not result["ok"], "expected re-bind refusal")
    _assert("already bound" in result["error"], f"expected 'already bound' error: {result['error']}")
    print("  refused with 'already bound' error")

    # ---- Test 9: unbound_renders surfaces non-bound post-v1 ----
    print("\nTest 9: unbound_renders includes test_d9 unbound rows")
    unbound = dispatcher.unbound_renders()
    unbound_ids = {r["id"] for r in unbound}
    # r2 (mismatch, not bound), r3 (multiple, not bound), r4 (orphan), r7 (mark_orphan)
    # r1 and r5 ARE bound. test_d9_r6 doesn't exist.
    expected_unbound = {"test_d9_r2", "test_d9_r3", "test_d9_r4", "test_d9_r7"}
    expected_bound = {"test_d9_r1", "test_d9_r5"}
    for rid in expected_unbound:
        _assert(rid in unbound_ids, f"{rid} should appear in unbound_renders")
    for rid in expected_bound:
        _assert(rid not in unbound_ids, f"{rid} (bound) should NOT appear in unbound_renders")
    print(f"  surfaced {len(expected_unbound)} unbound; correctly excluded {len(expected_bound)} bound")

    print("\nTest 10: cleanup")
    cleanup()
    unbound_after = dispatcher.unbound_renders()
    _assert(not any(r["id"].startswith("test_d9_") for r in unbound_after),
            "leftover test rows after cleanup")
    print("  state.db + YAMLs clean of test_d9_")

    print("\nPASS: all Day 9 binding behaviors verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
