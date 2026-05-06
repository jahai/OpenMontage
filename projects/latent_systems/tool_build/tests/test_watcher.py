#!/usr/bin/env python3
"""End-to-end test for tool_build/watcher.py.

Exercises file lifecycle (create → rename → modify → delete), persistence
across restart, and 3b.7 hash-stable identity across rename. Uses a temp
dir to avoid touching the user's actual Downloads.

Run: python tool_build/tests/test_watcher.py
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

# Make tool_build/ importable when invoked from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watcher import DownloadWatcher  # noqa: E402


SETTLE = 0.5  # generous delay for watchdog event delivery on Windows


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        pending_file = tmp_path / "_pending_downloads.json"

        w = DownloadWatcher(downloads_path=downloads, pending_file=pending_file)
        w.start()
        try:
            # 1. Create a watched file.
            f1 = downloads / "test_render_0.png"
            f1.write_bytes(b"hello world")
            time.sleep(SETTLE)
            pending = w.pending()
            _assert(str(f1) in pending, f"created file not tracked: {f1}")
            hash1 = pending[str(f1)]["hash"]
            first_seen1 = pending[str(f1)]["first_seen"]
            print(f"  [1] created {f1.name}: hash={hash1[:12]}…")

            # 2. Rename — hash should be preserved (3b.7), first_seen carries.
            f2 = downloads / "test_render_renamed.png"
            f1.rename(f2)
            time.sleep(SETTLE)
            pending = w.pending()
            _assert(str(f1) not in pending, "old path still tracked after rename")
            _assert(str(f2) in pending, f"new path not tracked: {f2}")
            _assert(pending[str(f2)]["hash"] == hash1,
                    f"hash changed across rename: {pending[str(f2)]['hash']} vs {hash1}")
            _assert(pending[str(f2)]["first_seen"] == first_seen1,
                    "first_seen reset across rename (should preserve)")
            print(f"  [2] renamed -> {f2.name}: hash preserved, first_seen preserved")

            # 3. Modify content — hash should change.
            f2.write_bytes(b"different content now, rehash needed")
            time.sleep(SETTLE)
            pending = w.pending()
            hash2 = pending[str(f2)]["hash"]
            _assert(hash2 != hash1, f"hash didn't change after content modification")
            print(f"  [3] modified content: hash {hash1[:8]} -> {hash2[:8]}")

            # 4. Drop a non-watched file (.txt) — should be ignored.
            ftxt = downloads / "ignore_me.txt"
            ftxt.write_text("not a render")
            time.sleep(SETTLE)
            pending = w.pending()
            _assert(str(ftxt) not in pending, ".txt file should not be tracked")
            print(f"  [4] non-watched extension ignored")

            # 5. Delete watched file — should be removed from pending.
            f2.unlink()
            time.sleep(SETTLE)
            pending = w.pending()
            _assert(str(f2) not in pending, f"deleted file still tracked: {f2}")
            print(f"  [5] deleted file removed from pending")

            # 6. Persistence across restart — drop a file, stop watcher,
            #    reload from disk, verify state survives.
            f3 = downloads / "persistent.png"
            f3.write_bytes(b"survives restart")
            time.sleep(SETTLE)
            saved_pending = w.pending()
            _assert(str(f3) in saved_pending, "f3 not tracked before restart")
            saved_hash = saved_pending[str(f3)]["hash"]

            w.stop()
            # New watcher instance reading the same JSON file.
            w2 = DownloadWatcher(downloads_path=downloads, pending_file=pending_file)
            reloaded = w2.pending()
            _assert(str(f3) in reloaded, "persistence failed: f3 not in reloaded state")
            _assert(reloaded[str(f3)]["hash"] == saved_hash,
                    "persistence: hash mismatch after reload")
            print(f"  [6] persistence: state survived watcher restart")

            # 7. reconcile() prunes deleted files, refreshes existing.
            f3.unlink()
            summary = w2.reconcile()
            _assert(summary["pruned"] >= 1, f"reconcile didn't prune deleted file: {summary}")
            _assert(str(f3) not in w2.pending(), "reconcile didn't remove deleted file")
            print(f"  [7] reconcile prunes stale entries: {summary}")

            # 8. find_by_hash() locates entries by content hash.
            #    Start observer FIRST, then write file so on_created fires.
            w2.start()
            try:
                f4 = downloads / "findable.png"
                f4.write_bytes(b"unique content for hash lookup")
                time.sleep(SETTLE)
                _assert(str(f4) in w2.pending(),
                        f"f4 not picked up by running observer")
                found_hash = w2.pending()[str(f4)]["hash"]
                matches = w2.find_by_hash(found_hash)
                _assert(str(f4) in matches, "find_by_hash didn't return f4")
                print(f"  [8] find_by_hash returns expected paths")
            finally:
                w2.stop()

        finally:
            w.stop()

    print("\nPASS: all watcher behaviors verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
