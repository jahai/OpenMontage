#!/usr/bin/env python3
"""Smoke tests for tool_build/router_tail.py.

Test 1 — parser only: synthesize log content, verify _parse_actions
yields the expected event dicts. Pure unit test, no I/O.

Test 2 — ingest end-to-end: monkey-patch the module-level ROUTER_LOG +
CURSOR_FILE to temp paths, drop a fake destination file under
tool_build/_data/_test_routing/<...>, run ingest, verify a renders
row was inserted with correct fields. Clean up state.db row + temp
files at end.

Run: python tool_build/tests/test_router_tail.py
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
import router_tail  # noqa: E402


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def test_parser() -> None:
    sample = """\
# Downloads router log

## Router run 2026-05-04T10:00:00
- Mode: interactive
- Files scanned: 3
- Tiers: high=2 medium=0 low=0 duplicate=1

- `nycwillow_test_concept_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee_0.png` → `shared/visual_identity_phase1_references/2_architectural_inhabitant/run_2026-05-04/nycwillow_test_concept_0.png`: moved | confidence=high | reason: keyword match 'institutional chamber'
- `ChatGPT Image May 4, 2026, 10_15_30 AM.png` → `shared/visual_identity_phase1_references/_inbox/chatgpt_inbox_001.png`: moved-to-inbox | confidence=low | reason: no taxonomy match
- `dupe_render.png` → ``: deleted | confidence=duplicate | reason: hash matches existing canonical
"""
    events = list(router_tail._parse_actions(sample))
    _assert(len(events) == 3, f"expected 3 parsed events, got {len(events)}")

    e1 = events[0]
    _assert(e1["timestamp"] == "2026-05-04T10:00:00", f"e1 timestamp: {e1['timestamp']}")
    _assert(e1["action"] == "moved", f"e1 action: {e1['action']}")
    _assert(e1["confidence"] == "high", f"e1 confidence: {e1['confidence']}")
    _assert("nycwillow_test_concept" in e1["source"], f"e1 source: {e1['source']}")
    _assert("2_architectural_inhabitant" in e1["destination"], f"e1 destination: {e1['destination']}")

    e2 = events[1]
    _assert(e2["action"] == "moved-to-inbox", f"e2 action: {e2['action']}")
    _assert(e2["confidence"] == "low", f"e2 confidence: {e2['confidence']}")

    e3 = events[2]
    _assert(e3["action"] == "deleted", f"e3 action: {e3['action']}")
    _assert(e3["confidence"] == "duplicate", f"e3 confidence: {e3['confidence']}")

    print("  [parser] 3 events parsed correctly")


def _ingest_roundtrip(repo_root: Path) -> None:
    """Drop a fake destination file under tool_build/_data/_test_routing/,
    write a synthetic router_log entry pointing to it, run ingest,
    verify a renders row was created. Clean up at end."""

    test_dir = db.DATA_DIR / "_test_routing"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "synthetic_route.png"
    test_file.write_bytes(b"synthetic routing test content")

    # Destination path is project-root-relative under projects/latent_systems/.
    # Our resolver looks for it under projects/latent_systems/, so we encode
    # the destination as tool_build/_data/_test_routing/synthetic_route.png.
    destination_rel = "tool_build/_data/_test_routing/synthetic_route.png"

    synthetic_log = (
        "## Router run 2026-05-04T11:00:00\n"
        "- Mode: interactive\n"
        "- Files scanned: 1\n"
        "- Tiers: high=1 medium=0 low=0 duplicate=0\n"
        "\n"
        f"- `synthetic_route.png` → `{destination_rel}`: moved | "
        "confidence=high | reason: synthetic test\n"
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        temp_log = tmp_path / "router_log.md"
        temp_log.write_text(synthetic_log, encoding="utf-8")
        temp_cursor = tmp_path / "_cursor.json"

        # Also seed a fake pending_downloads entry so we can verify
        # download_hash gets populated.
        pending_file = db.DATA_DIR / "_pending_downloads.json"
        pending_backup = pending_file.read_text(encoding="utf-8") if pending_file.exists() else None
        try:
            existing = json.loads(pending_backup) if pending_backup else {"version": "0001", "pending": {}}
            fake_pending_path = "C:/Users/josep/Downloads/synthetic_route.png"
            existing.setdefault("pending", {})[fake_pending_path] = {
                "hash": "fake_download_hash_abcdef1234567890" * 2,
                "first_seen": "2026-05-04T10:59:00+00:00",
                "last_seen": "2026-05-04T10:59:00+00:00",
                "size_bytes": 30,
            }
            pending_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")

            # Monkey-patch module-level constants to redirect at temp files.
            orig_log = router_tail.ROUTER_LOG
            orig_cursor = router_tail.CURSOR_FILE
            router_tail.ROUTER_LOG = temp_log
            router_tail.CURSOR_FILE = temp_cursor
            try:
                summary = router_tail.ingest(repo_root=repo_root, verbose=True)
            finally:
                router_tail.ROUTER_LOG = orig_log
                router_tail.CURSOR_FILE = orig_cursor

            print(f"  [ingest] summary: {summary}")
            _assert(summary["parsed"] == 1, f"expected 1 parsed, got {summary['parsed']}")
            _assert(summary["ingested"] == 1, f"expected 1 ingested, got {summary['ingested']}")

            # Verify renders row.
            with db.connect() as conn:
                row = conn.execute(
                    "SELECT id, filepath, tool, download_hash, canonical_hash, "
                    "discipline_version, hero_status, yaml_path "
                    "FROM renders WHERE filepath = ?",
                    (f"projects/latent_systems/{destination_rel}",),
                ).fetchone()

            _assert(row is not None, "renders row not inserted")
            (rid, fp, tool, dh, ch, dv, hs, yp) = row
            print(f"  [ingest] inserted: id={rid} tool={tool} discipline={dv}")
            _assert(dv == "1.0", f"discipline_version not 1.0: {dv}")
            _assert(dh is not None and "fake_download_hash" in dh,
                    f"download_hash not populated from pending: {dh}")
            _assert(hs is None, f"hero_status should be None for non-winner path: {hs}")
            _assert(yp.endswith(".yaml"), f"yaml_path not set: {yp}")

            # Verify YAML file written.
            yaml_abs = repo_root / yp
            _assert(yaml_abs.exists(), f"yaml file missing at {yaml_abs}")

            # Cleanup: delete the renders row + yaml file.
            with db.connect() as conn:
                conn.execute("DELETE FROM renders WHERE id = ?", (rid,))
                conn.commit()
            yaml_abs.unlink()
            print(f"  [ingest] cleaned up: row deleted, yaml deleted")

        finally:
            # Restore pending_downloads.json
            if pending_backup is not None:
                pending_file.write_text(pending_backup, encoding="utf-8")
            elif pending_file.exists():
                pending_file.unlink()

    # Cleanup test dir
    test_file.unlink()
    test_dir.rmdir()


def main() -> int:
    import subprocess
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    repo_root = Path(out.stdout.strip())

    print("Test 1: parser")
    test_parser()
    print("Test 2: ingest roundtrip")
    _ingest_roundtrip(repo_root)

    print("\nPASS: all router_tail behaviors verified")
    return 0


def test_main():
    """SKIPPED under pytest — main() includes _ingest_roundtrip which
    writes files via `db.DATA_DIR` (monkey-patched to tmp_path by the
    isolated_db fixture) but resolves them via `repo_root + canonical
    path` (real repo). The fixture necessarily diverges these two
    resolution chains, so _ingest_roundtrip can't pass under the fixture.

    test_parser above is pytest-discovered directly and runs cleanly under
    the fixture. _ingest_roundtrip's coverage comes from standalone
    `python tests/test_router_tail.py` invocation, which uses the real
    `_data/` and validates real-repo file resolution.

    Future cleanup option: refactor _ingest_roundtrip to a pure unit test
    that mocks the file resolver, removing the real-file dependency."""
    import pytest
    pytest.skip("_ingest_roundtrip requires real-repo file structure "
                "incompatible with tmp_path fixture; covered by standalone run")


if __name__ == "__main__":
    sys.exit(main())
