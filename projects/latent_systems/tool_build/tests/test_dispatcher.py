#!/usr/bin/env python3
"""Smoke test for tool_build/dispatcher.py.

Tests prompt creation, dispatch (with clipboard + browser DISABLED to
avoid side effects), and re-roll attempt numbering. Cleans up state.db
rows + YAML files at end so the test is repeatable.

Run: python tool_build/tests/test_dispatcher.py
"""

from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
import dispatcher  # noqa: E402


def _assert(cond, msg):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    print("Test 1: create_prompt + verify YAML + db row")
    record = dispatcher.create_prompt(
        prompt_text="Cinematic film still. Test prompt for dispatcher smoke. --ar 16:9 --v 7",
        tool="midjourney",
    )
    pid = record["id"]
    print(f"  created prompt id={pid}")

    # Verify db row
    with db.connect() as conn:
        row = conn.execute("SELECT id, tool, status, discipline_version FROM prompts WHERE id=?", (pid,)).fetchone()
    _assert(row is not None, "prompt row not in db")
    _assert(row[1] == "midjourney", f"tool: {row[1]}")
    _assert(row[2] == "draft", f"status: {row[2]} (expected draft)")
    _assert(row[3] == "1.0", f"discipline_version: {row[3]}")
    print(f"  db row: tool={row[1]}, status={row[2]}, discipline={row[3]}")

    # Verify YAML
    text = dispatcher.get_prompt_text(pid)
    _assert(text and "Cinematic film still" in text, "YAML text missing or wrong")
    print(f"  yaml round-trip: {text[:60]}...")

    print("\nTest 2: dispatch (clipboard + browser DISABLED) -> attempt + status update")
    summary = dispatcher.dispatch(
        prompt_id=pid, prompt_text=text, tool="midjourney",
        write_clipboard=False, open_url=False,
    )
    print(f"  dispatch summary: {summary}")
    _assert(summary["attempt_number"] == 1, f"attempt_number: {summary['attempt_number']}")
    _assert(summary["attempt_id"], "attempt_id missing")
    _assert(not summary["errors"], f"unexpected errors: {summary['errors']}")
    _assert(not summary["clipboard_written"], "clipboard_written should be False (disabled)")
    _assert(not summary["browser_opened"], "browser_opened should be False (disabled)")

    # Verify status transition + attempt row.
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM prompts WHERE id=?", (pid,)).fetchone()
        _assert(row[0] == "awaiting_return", f"status after dispatch: {row[0]}")
        att = conn.execute(
            "SELECT attempt_number, status, trigger_method FROM generation_attempts WHERE prompt_id=?",
            (pid,)
        ).fetchall()
    _assert(len(att) == 1, f"expected 1 attempt, got {len(att)}")
    _assert(att[0] == (1, "in_flight", "clipboard_handoff"),
            f"attempt row: {att[0]}")
    print(f"  prompt status -> awaiting_return; 1 attempt row inserted")

    print("\nTest 3: re-roll dispatch -> attempt_number=2")
    summary2 = dispatcher.dispatch(
        prompt_id=pid, prompt_text=text, tool="midjourney",
        write_clipboard=False, open_url=False, notes="re-roll for testing",
    )
    _assert(summary2["attempt_number"] == 2, f"second attempt_number: {summary2['attempt_number']}")
    print(f"  re-roll attempt #2 created")

    print("\nTest 4: list_prompts includes our test prompt with attempt count")
    prompts = dispatcher.list_prompts(limit=100)
    found = [p for p in prompts if p["id"] == pid]
    _assert(found, f"created prompt not in list (got {len(prompts)} prompts)")
    _assert(found[0]["attempts"] == 2, f"attempt count wrong: {found[0]['attempts']}")
    print(f"  list_prompts returns prompt with attempts={found[0]['attempts']}")

    print("\nTest 5: cleanup")
    yaml_path = db.DATA_DIR / "prompts" / f"{pid}.yaml"
    with db.connect() as conn:
        conn.execute("DELETE FROM generation_attempts WHERE prompt_id=?", (pid,))
        conn.execute("DELETE FROM prompts WHERE id=?", (pid,))
        conn.commit()
    if yaml_path.exists():
        yaml_path.unlink()
    print(f"  cleaned: db rows deleted, yaml unlinked")

    print("\nPASS: dispatcher behaviors verified")
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_dispatcher.py` invocation
    remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
