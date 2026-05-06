"""Filesystem watcher for ~/Downloads/ — Phase 1 substrate per Section 4.

Day 5 scope: watcher primitive only. Detects render-extension files
(.png/.mp4/.mp3) appearing in Downloads, hashes them at first detection,
preserves hash identity across rename (3b.7), persists state across
restart.

Out of scope today (Days 6-9):
- Routing files into canonical structure (existing router does that)
- Clipboard handoff for MJ (Feature 3b)
- 3b.1-3b.8 failure-mode timers
- generation_attempts row creation
- render → attempt → prompt binding

Storage shape (transient operational state, not artifact-layer):
    _data/_pending_downloads.json:
        {
          "version": "0001",
          "downloads_path": "<resolved abs path>",
          "pending": {
            "<abs file path>": {
              "hash": "<sha256>",
              "first_seen": "<iso>",
              "last_seen": "<iso>",
              "size_bytes": <int>
            },
            ...
          }
        }

Why JSON not state.db: pending downloads are transient operational
state (mirrors _retry_queue.yaml in Section 5). Promoting to a state.db
table is a Phase 2 decision once usage patterns inform the schema.

Two invocation modes:
    python tool_build/watcher.py --once     # one-shot scan and hash
    python tool_build/watcher.py --daemon   # block; watch indefinitely

Server-integrated path: runtime.py starts/stops the watcher in lifespan.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

import db


WATCHED_EXTENSIONS = (".png", ".mp4", ".mp3")
PENDING_FILE = db.DATA_DIR / "_pending_downloads.json"
ROUTER_CONFIG = db.TOOL_BUILD_DIR.parent / "tools" / "router_config.yaml"
PENDING_VERSION = "0001"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_downloads_path() -> Path:
    """Resolve the platform's Downloads path from router_config.yaml.

    Falls back to ~/Downloads if the config is missing/unparseable.
    """
    fallback = Path.home() / "Downloads"
    try:
        with ROUTER_CONFIG.open(encoding="utf-8") as f:
            config = yaml.safe_load(f)
        paths = (config or {}).get("downloads_path") or {}
        sysname = platform.system().lower()  # 'windows', 'darwin', 'linux'
        raw = paths.get(sysname)
        if not raw:
            return fallback
        return Path(raw).expanduser()
    except (OSError, yaml.YAMLError):
        return fallback


def _is_watched(path: Path) -> bool:
    return path.suffix.lower() in WATCHED_EXTENSIONS


def _sha256_of(path: Path, chunk_size: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk_size)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


class DownloadWatcher(FileSystemEventHandler):
    """Watchdog handler + persistence layer for Downloads tracking.

    Thread-safe: watchdog calls handlers from the observer thread; CLI/
    server reads happen on different threads. All state mutations go
    through self._lock.
    """

    def __init__(self, downloads_path: Optional[Path] = None,
                 pending_file: Optional[Path] = None) -> None:
        super().__init__()
        self._downloads_path = downloads_path or _resolve_downloads_path()
        self._pending_file = pending_file or PENDING_FILE
        self._lock = threading.Lock()
        self._pending: dict[str, dict] = {}
        self._observer: Optional[Observer] = None
        self._load()

    @property
    def downloads_path(self) -> Path:
        return self._downloads_path

    def pending(self) -> dict[str, dict]:
        """Return a snapshot copy of pending state."""
        with self._lock:
            return {k: dict(v) for k, v in self._pending.items()}

    def find_by_hash(self, sha256: str) -> list[str]:
        """Return paths whose recorded hash matches sha256."""
        with self._lock:
            return [p for p, e in self._pending.items() if e.get("hash") == sha256]

    # --- persistence ---

    def _load(self) -> None:
        if not self._pending_file.exists():
            return
        try:
            data = json.loads(self._pending_file.read_text(encoding="utf-8"))
            if data.get("version") == PENDING_VERSION:
                self._pending = dict(data.get("pending", {}))
        except (OSError, json.JSONDecodeError):
            # Corrupt or unreadable — start clean. Next persist overwrites.
            self._pending = {}

    def _persist(self) -> None:
        # Caller holds self._lock.
        self._pending_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": PENDING_VERSION,
            "downloads_path": str(self._downloads_path),
            "pending": self._pending,
        }
        tmp = self._pending_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._pending_file)

    # --- core operations ---

    def _record(self, abs_path: str, hash_value: str, size: int) -> None:
        # Caller holds self._lock.
        existing = self._pending.get(abs_path)
        now = _iso_now()
        if existing and existing.get("hash") == hash_value:
            existing["last_seen"] = now
            existing["size_bytes"] = size
        else:
            self._pending[abs_path] = {
                "hash": hash_value,
                "first_seen": existing.get("first_seen", now) if existing else now,
                "last_seen": now,
                "size_bytes": size,
            }
        self._persist()

    def _forget(self, abs_path: str) -> None:
        # Caller holds self._lock.
        if abs_path in self._pending:
            del self._pending[abs_path]
            self._persist()

    def _hash_and_record(self, path: Path) -> None:
        """Hash the file and record it. Tolerates transient errors."""
        if not _is_watched(path):
            return
        try:
            if not path.exists() or not path.is_file():
                return
            size = path.stat().st_size
            h = _sha256_of(path)
        except (OSError, PermissionError):
            # File vanished, locked by another writer, or unreadable.
            # Watcher will see another modify event when writer releases.
            return
        with self._lock:
            self._record(str(path), h, size)

    # --- watchdog event handlers ---

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._hash_and_record(Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._hash_and_record(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = str(event.src_path)
        dest = str(event.dest_path) if event.dest_path else None
        with self._lock:
            entry = self._pending.get(src)
            if entry is not None:
                # Preserve hash identity across rename (3b.7). first_seen
                # carries forward; last_seen updates.
                if dest is not None and _is_watched(Path(dest)):
                    new_entry = dict(entry)
                    new_entry["last_seen"] = _iso_now()
                    self._pending[dest] = new_entry
                del self._pending[src]
                self._persist()
        # If the dest is a watched file but we had no entry for src
        # (renamed in from outside the directory, or src wasn't watched),
        # treat it as a new file.
        if dest and _is_watched(Path(dest)):
            with self._lock:
                if dest not in self._pending:
                    # Need to release lock before hashing — _hash_and_record
                    # acquires its own. Drop lock and call.
                    pass
            if dest not in self._pending:
                self._hash_and_record(Path(dest))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        with self._lock:
            self._forget(str(event.src_path))

    # --- lifecycle ---

    def reconcile(self) -> dict:
        """Walk Downloads dir once and reconcile state.

        Catches files that appeared while watcher wasn't running, and
        prunes entries for files that have since been deleted.
        Returns summary: {scanned, added, refreshed, pruned}.
        """
        summary = {"scanned": 0, "added": 0, "refreshed": 0, "pruned": 0}
        seen: set[str] = set()
        if not self._downloads_path.exists():
            return summary
        for p in self._downloads_path.iterdir():
            if not p.is_file() or not _is_watched(p):
                continue
            summary["scanned"] += 1
            abs_path = str(p)
            seen.add(abs_path)
            try:
                size = p.stat().st_size
                h = _sha256_of(p)
            except (OSError, PermissionError):
                continue
            with self._lock:
                existing = self._pending.get(abs_path)
                if existing and existing.get("hash") == h:
                    existing["last_seen"] = _iso_now()
                    existing["size_bytes"] = size
                    summary["refreshed"] += 1
                else:
                    is_new = existing is None
                    self._record(abs_path, h, size)
                    summary["added"] += 1 if is_new else 0
                    summary["refreshed"] += 0 if is_new else 1
        # Prune entries that no longer exist on disk.
        with self._lock:
            stale = [p for p in self._pending if p not in seen]
            for p in stale:
                del self._pending[p]
                summary["pruned"] += 1
            if stale:
                self._persist()
        return summary

    def start(self) -> None:
        """Start the watchdog observer in a background thread."""
        if self._observer is not None:
            return
        if not self._downloads_path.exists():
            self._downloads_path.mkdir(parents=True, exist_ok=True)
        obs = Observer()
        obs.schedule(self, str(self._downloads_path), recursive=False)
        obs.start()
        self._observer = obs

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5.0)
        self._observer = None


# --- standalone CLI ---

if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true",
                      help="reconcile once and exit (scan + hash)")
    mode.add_argument("--daemon", action="store_true",
                      help="watch Downloads indefinitely (Ctrl+C to stop)")
    parser.add_argument("--downloads-path", type=Path, default=None,
                        help="override watched directory (test/debug)")
    parser.add_argument("--pending-file", type=Path, default=None,
                        help="override pending state file (test/debug)")
    args = parser.parse_args()

    w = DownloadWatcher(downloads_path=args.downloads_path,
                         pending_file=args.pending_file)
    print(f"[watcher] downloads path: {w.downloads_path}")

    if args.once:
        summary = w.reconcile()
        print(f"[watcher] reconcile summary: {summary}")
        print(f"[watcher] pending count: {len(w.pending())}")
        sys.exit(0)

    # --daemon
    summary = w.reconcile()
    print(f"[watcher] initial reconcile: {summary}")
    w.start()
    print(f"[watcher] watching {w.downloads_path}; Ctrl+C to stop")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("[watcher] stopping ...")
    finally:
        w.stop()
        print(f"[watcher] final pending count: {len(w.pending())}")
