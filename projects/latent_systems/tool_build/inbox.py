"""In-app pending-downloads inbox (Phase 2.5 workflow gap fix).

Closes the web-UI ingestion gap surfaced 2026-05-08: MJ/Kling web-UI
generations land in `~/Downloads`, watcher hashes them into
`pending_downloads.json`, but no path creates `renders` rows without
an in-flight prompt attempt to bind to. Without this module, Joseph
cp's each file to canonical paths manually then runs the walker.

This module provides:
  - list_pending() — image files watcher knows about, with metadata +
    suggested destination from filename heuristics
  - suggest_destination(filename) — pure heuristic mapping filename
    patterns to canonical subpaths (override-able from UI)
  - ingest_file(source_path, destination_dir) — copy file to canonical
    path + invoke walker so the new file appears as a `renders` row,
    audit-grid-visible, ready for verdict + consultation

AD-5 guard: ingest refuses any destination outside
`projects/latent_systems/`. Within that subtree, Joseph picks the
destination via UI (writing to canonical paths is part of normal
audit workflow; AD-5's hook only blocks Claude COMMITS to those
paths, not runtime app writes initiated by Joseph).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

import db
import runtime
import walker


# Destination heuristics — (filename regex, canonical subpath).
# Patterns are checked in order; first match wins. The default fallback
# (last entry) catches everything else.
_DESTINATION_HEURISTICS: list[tuple[re.Pattern[str], str]] = [
    # H#3 reenactment work — 1930s anchor/state renders
    (re.compile(r"1930s|skinner|h3_|h#3|rat_(anchor|state)", re.IGNORECASE),
     "projects/latent_systems/shared/h3_reenactment_phase3/anchors/"),
    # Default: by-design Phase 2 visual-identity evaluation hold queue
    (re.compile(r".*"),
     "projects/latent_systems/shared/visual_identity_phase1_references/_inbox/"),
]


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def list_pending() -> list[dict]:
    """Return pending-download image files with metadata + suggested destination.

    Filters applied:
      - image extensions only (audit viewer is image-focused; videos
        can be added later when the viewer supports them)
      - file exists on disk (skip stale hash entries the watcher hasn't pruned)
      - hash NOT already in `renders.canonical_hash` (skip files already
        ingested at a canonical path — the inbox shows actionable items,
        not historical ones)

    Sort: newest first by `first_seen`, so freshly-generated work surfaces
    at the top.
    """
    w = runtime.get_download_watcher()
    if w is None:
        return []

    # Hashes of already-ingested files — skip these in the inbox to avoid
    # showing the same content twice (once in inbox as Downloads path,
    # once in audit grid as canonical-path render).
    conn = db.connect()
    try:
        ingested_hashes = {
            r[0] for r in conn.execute(
                "SELECT canonical_hash FROM renders WHERE canonical_hash IS NOT NULL"
            ).fetchall()
        }
    finally:
        conn.close()

    items: list[dict] = []
    for path_str, meta in w.pending().items():
        p = Path(path_str)
        if not p.exists():
            continue
        if p.suffix.lower() not in _IMAGE_EXTS:
            continue
        if meta.get("hash") in ingested_hashes:
            continue
        items.append({
            "path": str(p),
            "filename": p.name,
            "hash": meta.get("hash"),
            "size_bytes": meta.get("size_bytes", 0),
            "first_seen": meta.get("first_seen"),
            "suggested_destination": suggest_destination(p.name),
        })
    items.sort(key=lambda x: x["first_seen"] or "", reverse=True)
    return items


def suggest_destination(filename: str) -> str:
    """Return suggested canonical subpath (relative to repo_root) for a filename."""
    for pattern, dest in _DESTINATION_HEURISTICS:
        if pattern.search(filename):
            return dest
    return _DESTINATION_HEURISTICS[-1][1]


def ingest_file(
    *,
    source_path: str,
    destination_dir: str,
    repo_root: Optional[Path] = None,
) -> dict:
    """Copy file from source (Downloads) to destination_dir + run walker.

    `destination_dir` is repo-root-relative (e.g.,
    "projects/latent_systems/shared/h3_reenactment_phase3/anchors/").

    Returns dict:
      - on success: {ok: True, render_id: <id>, dest_path: <rel>,
                     walker_summary: <dict>}
      - on validation failure: {ok: False, error: <code>, message: <str>}

    Error codes:
      - source_not_found — source file doesn't exist
      - dest_not_found — destination directory doesn't exist
      - dest_not_dir — destination path exists but isn't a directory
      - ad5_violation — destination outside projects/latent_systems/
      - dest_exists — file with same name already at destination
    """
    if repo_root is None:
        repo_root = db.REPO_ROOT
    repo_root = Path(repo_root)

    source = Path(source_path)
    if not source.exists():
        return {"ok": False, "error": "source_not_found",
                "message": f"source file not found: {source}"}

    # Resolve destination as repo-root-relative
    dest_dir = (repo_root / destination_dir).resolve()
    if not dest_dir.exists():
        return {"ok": False, "error": "dest_not_found",
                "message": f"destination directory not found: {destination_dir}"}
    if not dest_dir.is_dir():
        return {"ok": False, "error": "dest_not_dir",
                "message": f"destination is not a directory: {destination_dir}"}

    # AD-5 guard: refuse anywhere outside latent_systems/
    try:
        rel_dest = dest_dir.relative_to(repo_root.resolve())
    except ValueError:
        return {"ok": False, "error": "ad5_violation",
                "message": "destination must be within the repo"}
    rel_dest_str = str(rel_dest).replace("\\", "/")
    if not rel_dest_str.startswith("projects/latent_systems"):
        return {"ok": False, "error": "ad5_violation",
                "message": (
                    "destination must be under projects/latent_systems/; "
                    f"got: {rel_dest_str}"
                )}

    dest_path = dest_dir / source.name
    if dest_path.exists():
        return {"ok": False, "error": "dest_exists",
                "message": (
                    "a file with this name already exists at destination: "
                    f"{(dest_path.relative_to(repo_root.resolve())).as_posix()}"
                )}

    # Copy (preserves metadata)
    shutil.copy2(source, dest_path)

    # Invoke walker — single full walk picks up the new file + classifies
    walker_summary = walker.walk(repo_root=repo_root, dry_run=False, verbose=False)

    # Resolve the new render_id by canonical_hash + filepath match
    canonical_hash = walker.sha256_of(dest_path)
    rel_dest_path = dest_path.relative_to(repo_root.resolve()).as_posix()
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT id FROM renders WHERE canonical_hash = ? AND filepath = ?",
            (canonical_hash, rel_dest_path),
        ).fetchone()
    finally:
        conn.close()

    return {
        "ok": True,
        "render_id": row[0] if row else None,
        "dest_path": rel_dest_path,
        "walker_summary": walker_summary,
    }
