"""Router log tailer — translates router_log.md routing events into
state.db renders rows + YAML representations.

Day 6 scope: parse the log per the format documented in
tools/router_log.md, ingest new events incrementally via byte-offset
cursor, populate renders rows. attempt_id and prompt_id stay NULL —
Day 9 wires up generation_attempts and prompt binding.

Why poll over watchdog? Router is user-initiated and runs are bursty
+ infrequent. A 10s asyncio poll in the server lifespan adds minimal
overhead and avoids the complexity of layering a second watchdog
observer for the log file specifically.

Idempotency: cursor file (_data/_router_log_cursor.json) tracks byte
offset of last processed content. If router_log is rewritten or
truncated, cursor falls back to 0 and re-parses; the
existing_render(canonical_hash, filepath) check from walker.py
prevents duplicate rows.

Coexistence: tailer reads tools/router_log.md (Section 4 declared
read source). Writes only to _data/. AD-5 preserved.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import yaml

import db
from constants import CURRENT_DISCIPLINE_VERSION
from walker import classify, render_yaml, sha256_of, existing_render, insert_render


ROUTER_LOG = db.TOOL_BUILD_DIR.parent / "tools" / "router_log.md"
CURSOR_FILE = db.DATA_DIR / "_router_log_cursor.json"
DISCIPLINE_NEW = CURRENT_DISCIPLINE_VERSION  # was hardcoded "1.0"; now centralized per Day 5-9 review §4.4

# Match a single action line:
#   - `<source>` → `<destination>`: <action> | confidence=<tier> | reason: <text>
#
# Code-review (Day 5-9 §4.3): verified against tools/downloads_router.py
# log-writer at lines 423-426. Real format from execute_classification:
#   - Routing entries (MOVED, FAILED, WOULD-MOVE): include backticked
#     source + ` → ` + backticked destination + `: ` + ACTION + ` | `
#     confidence=<tier> + ` | reason: <text>`. Match this regex.
#   - DUPLICATE entries (lines 386-389): only `- `<name>`: <action>` with
#     no destination + no `→` + no confidence. Don't match — silently
#     skipped at parse time (correct: duplicates don't create renders).
#   - SKIPPED entries (lines 395, 404): same shape as DUPLICATE. Skipped.
#
# ROUTING_ACTIONS lowercases via _parse_actions, so MOVED -> moved matches.
# FAILED/WOULD-MOVE/SKIPPED/DUPLICATE intentionally NOT in allowlist.
ACTION_RE = re.compile(
    r"^- `(?P<source>[^`]+)` → `(?P<destination>[^`]*)`: "
    r"(?P<action>[^|]+?) \| confidence=(?P<confidence>\w+)"
    r"(?: \| reason: (?P<reason>.*))?$"
)

# Match a run header so we can scope actions and timestamp them.
# Real format from line 581: "\n## Router run {datetime.isoformat()}"
RUN_HEADER_RE = re.compile(r"^## Router run (?P<timestamp>\S+)\s*$")

# Routing actions that produce a canonical render. After lowercase folding:
#   - 'moved' (real router: MOVED on successful routing — verified)
#   - 'copied'/'routed' (forward-compat — not currently emitted by router)
#   - 'moved-to-inbox'/'moved-to-deprecated' (forward-compat for action-word evolution)
# Intentionally excludes:
#   - 'failed (...)' — file didn't actually route
#   - 'would-move (dry-run)' — dry-run, file untouched
#   - 'duplicate'/'skipped' — caught by regex non-match (no destination)
ROUTING_ACTIONS = {"moved", "copied", "routed", "moved-to-inbox", "moved-to-deprecated"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_cursor() -> int:
    if not CURSOR_FILE.exists():
        return 0
    try:
        data = json.loads(CURSOR_FILE.read_text(encoding="utf-8"))
        return int(data.get("offset", 0))
    except (OSError, json.JSONDecodeError, ValueError):
        return 0


def _write_cursor(offset: int) -> None:
    CURSOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"offset": offset, "updated": _iso_now()}
    tmp = CURSOR_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(CURSOR_FILE)


def _read_new_content(log_path: Path, cursor: int) -> tuple[str, int]:
    """Return (new_content, new_cursor). If cursor exceeds file size
    (file truncated/rewritten), reset to 0 and return whole file."""
    if not log_path.exists():
        return "", cursor
    size = log_path.stat().st_size
    if cursor > size:
        cursor = 0
    with log_path.open("r", encoding="utf-8") as f:
        f.seek(cursor)
        content = f.read()
    return content, size


def _parse_actions(content: str) -> Iterable[dict]:
    """Yield parsed action dicts from new log content.

    Each yielded dict: {timestamp, source, destination, action,
    confidence, reason}. Skips lines that don't match either header or
    action regex (template comments, blank lines, etc.).
    """
    current_run: Optional[str] = None
    for line in content.splitlines():
        run_match = RUN_HEADER_RE.match(line)
        if run_match:
            current_run = run_match.group("timestamp")
            continue
        action_match = ACTION_RE.match(line)
        if action_match:
            d = action_match.groupdict()
            d["timestamp"] = current_run
            d["action"] = d["action"].strip().lower()
            yield d


def _lookup_pending_hash(source_filename: str) -> Optional[str]:
    """Look up the download_hash for a source filename from pending_downloads."""
    pending_file = db.DATA_DIR / "_pending_downloads.json"
    if not pending_file.exists():
        return None
    try:
        data = json.loads(pending_file.read_text(encoding="utf-8"))
        pending = data.get("pending", {})
    except (OSError, json.JSONDecodeError):
        return None
    # Match by basename — pending paths are absolute Downloads paths;
    # router_log source is the basename.
    for path, entry in pending.items():
        if Path(path).name == source_filename:
            return entry.get("hash")
    return None


def _resolve_destination(repo_root: Path, destination: str) -> Optional[Path]:
    """Resolve router-logged destination to absolute path.

    Router log records project-root-relative paths under
    projects/latent_systems/. If the file doesn't exist at the resolved
    location, returns None (router may have failed mid-route, or path
    format may have changed).
    """
    candidate = repo_root / "projects" / "latent_systems" / destination
    if candidate.exists() and candidate.is_file():
        return candidate
    # Some destinations may already be absolute or partial — try as-is.
    direct = repo_root / destination
    if direct.exists() and direct.is_file():
        return direct
    return None


def ingest(*, repo_root: Optional[Path] = None, verbose: bool = False) -> dict:
    """Parse new router_log content, ingest routing events into state.db.

    Returns summary: {parsed, ingested, skipped_existing, skipped_action,
    skipped_no_file, errors, cursor_before, cursor_after}.
    """
    if repo_root is None:
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        repo_root = Path(out.stdout.strip())

    summary = {
        "parsed": 0, "ingested": 0, "skipped_existing": 0,
        "skipped_action": 0, "skipped_no_file": 0, "errors": 0,
        "cursor_before": 0, "cursor_after": 0,
    }
    summary["cursor_before"] = _read_cursor()
    content, new_cursor = _read_new_content(ROUTER_LOG, summary["cursor_before"])
    summary["cursor_after"] = new_cursor

    if not content:
        return summary

    renders_dir = db.DATA_DIR / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)

    conn = db.connect()
    try:
        for event in _parse_actions(content):
            summary["parsed"] += 1

            if event["action"] not in ROUTING_ACTIONS:
                summary["skipped_action"] += 1
                if verbose:
                    print(f"[tail] skip action='{event['action']}': {event['source']}")
                continue

            dest_abs = _resolve_destination(repo_root, event["destination"])
            if dest_abs is None:
                summary["skipped_no_file"] += 1
                if verbose:
                    print(f"[tail] skip (no file at destination): {event['destination']}")
                continue

            try:
                rel_to_repo = dest_abs.relative_to(repo_root).as_posix()
                filename = dest_abs.name
                canonical_hash = sha256_of(dest_abs)

                if existing_render(conn, canonical_hash, rel_to_repo):
                    summary["skipped_existing"] += 1
                    if verbose:
                        print(f"[tail] skip (already in renders): {rel_to_repo}")
                    continue

                # Stable id same scheme as walker: hash(content + "|" + path)
                render_id = hashlib.sha256(
                    f"{canonical_hash}|{rel_to_repo}".encode("utf-8")
                ).hexdigest()[:16]

                tool, variant = classify(filename)
                hero_status = "pre_v1_hero" if "winners" in dest_abs.parts else None
                yaml_rel = f"projects/latent_systems/tool_build/_data/renders/{render_id}.yaml"
                yaml_abs = renders_dir / f"{render_id}.yaml"
                created = _iso_now()

                download_hash = _lookup_pending_hash(event["source"])

                payload = render_yaml(
                    render_id=render_id, rel_path=rel_to_repo, filename=filename,
                    canonical_hash=canonical_hash, tool=tool, variant=variant,
                    hero_status=hero_status,
                )
                # Override discipline_version + add routing provenance.
                payload["discipline_version"] = DISCIPLINE_NEW
                payload["download_hash"] = download_hash
                payload["routed_from"] = event["source"]
                payload["routed_at"] = event["timestamp"]
                payload["routing_confidence"] = event["confidence"]
                payload["routing_reason"] = event.get("reason")
                payload["notes"] = (
                    f"Routed by tools/downloads_router.py at {event['timestamp']}; "
                    f"confidence={event['confidence']}."
                )

                with yaml_abs.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(payload, f, sort_keys=False,
                                   default_flow_style=False, allow_unicode=True)

                # Insert with override discipline_version (insert_render
                # hardcodes pre_v1; we patch via direct INSERT instead).
                conn.execute(
                    """
                    INSERT INTO renders (
                        id, attempt_id, prompt_id, filename, filepath,
                        download_hash, canonical_hash, tool, variant,
                        hero_status, discipline_version, yaml_path, created
                    ) VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (render_id, filename, rel_to_repo, download_hash,
                     canonical_hash, tool, variant, hero_status,
                     DISCIPLINE_NEW, yaml_rel, created),
                )
                conn.commit()  # per-file commit, matches walker pattern
                summary["ingested"] += 1

                # Day 9: attempt to auto-bind the freshly-ingested render
                # to an open generation_attempt. dispatcher.auto_bind_render
                # encodes the decision matrix (1+match, mismatch, multiple,
                # orphan). On no-bind paths it stamps the render YAML with
                # needs_review_reason for the /unbound_renders endpoint.
                try:
                    import dispatcher
                    bind_result = dispatcher.auto_bind_render(render_id)
                    summary.setdefault("bind_decisions", {})
                    decision = bind_result.get("decision", "unknown")
                    summary["bind_decisions"][decision] = (
                        summary["bind_decisions"].get(decision, 0) + 1
                    )
                except Exception as e:
                    print(f"[tail] WARN: auto_bind failed for {render_id}: {e}",
                          file=sys.stderr)

                if verbose:
                    print(f"[tail] ingested: {rel_to_repo} (tool={tool}, "
                          f"download_hash={'set' if download_hash else 'none'})")

            except (OSError, sqlite3.Error) as e:
                summary["errors"] += 1
                print(f"[tail] ERROR on {event}: {e}", file=sys.stderr)
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass

    finally:
        conn.close()

    # Advance cursor only if we got through the content without crashing.
    _write_cursor(new_cursor)
    summary["cursor_after"] = new_cursor
    return summary


# --- standalone CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset-cursor", action="store_true",
                        help="reset cursor to 0 and re-process whole log")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.reset_cursor:
        if CURSOR_FILE.exists():
            CURSOR_FILE.unlink()
        print("[tail] cursor reset")

    summary = ingest(verbose=args.verbose)
    print(f"[tail] summary: {summary}")
    sys.exit(1 if summary["errors"] else 0)
