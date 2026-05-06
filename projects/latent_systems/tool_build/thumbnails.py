"""Audit thumbnail cache (Phase 2 Wave A).

Per phase2_design_notes.md v0.4 §2 (audit_thumbnails table) + §5
(thumbnail-serve invalidation logic).

Generates downscaled JPEG copies of canonical render PNGs, cached at
`_data/_audit_thumbnails/<render_id>.jpg`. State.db `audit_thumbnails`
row tracks `source_hash` (= renders.canonical_hash at generation time)
for cache invalidation: serve_thumbnail() compares stored source_hash
against current canonical_hash and regenerates on mismatch.

Downscale target: max edge 1568px (Anthropic vision API limit per
design §1 4.8). JPEG output (rather than PNG) for smaller file size on
the grid view; quality 85 is the standard sweet spot.

Module-level guard: Pillow is the only Phase 2-specific dependency.
audit.py stays Pillow-free so unit tests against business logic don't
require image-processing dependencies. Code paths that need image
processing import this module explicitly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image

import db


THUMBNAIL_DIR = db.DATA_DIR / "_audit_thumbnails"

# Anthropic vision API max edge per phase2_design_notes §1 4.8.
MAX_EDGE_PX = 1568

# JPEG quality — 85 is standard sweet spot (visible quality drop only
# below ~75; gain above ~90 negligible against bytes cost).
JPEG_QUALITY = 85


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _abs_from_repo_relative(repo_relative: str) -> Path:
    """Convert a stored render filepath (repo-relative) to absolute path."""
    repo_root = db.TOOL_BUILD_DIR.parent.parent.parent
    return repo_root / repo_relative


def _thumbnail_abs_path(render_id: str) -> Path:
    """Cache-canonical thumbnail location for a render."""
    return THUMBNAIL_DIR / f"{render_id}.jpg"


def _thumbnail_relative_path(render_id: str) -> str:
    """Relative-to-_data thumbnail path stored in audit_thumbnails.thumbnail_path."""
    return f"_audit_thumbnails/{render_id}.jpg"


def get_or_generate(render_id: str) -> Optional[dict]:
    """Return thumbnail metadata for render_id, generating + caching if
    absent or stale.

    Returns dict {render_id, thumbnail_abs_path, source_hash, width,
    height, bytes, created} or None if:
      - render_id not in renders table, OR
      - render file missing on disk, OR
      - image processing failed (corrupt file / unsupported format).

    Cache invalidation: a thumbnail is fresh iff
    `audit_thumbnails.source_hash == renders.canonical_hash` AND the
    thumbnail file exists on disk. Either condition failing triggers
    regeneration.
    """
    conn = db.connect()
    try:
        render_row = conn.execute(
            "SELECT id, filepath, canonical_hash FROM renders WHERE id = ?",
            (render_id,),
        ).fetchone()
        if render_row is None:
            return None
        _, filepath, canonical_hash = render_row

        thumb_row = conn.execute(
            """
            SELECT render_id, thumbnail_path, source_hash, width, height,
                   bytes, created
            FROM audit_thumbnails WHERE render_id = ?
            """,
            (render_id,),
        ).fetchone()

        if thumb_row is not None and thumb_row[2] == canonical_hash:
            thumb_abs = _thumbnail_abs_path(render_id)
            if thumb_abs.exists():
                return {
                    "render_id": thumb_row[0],
                    "thumbnail_abs_path": thumb_abs,
                    "source_hash": thumb_row[2],
                    "width": thumb_row[3], "height": thumb_row[4],
                    "bytes": thumb_row[5], "created": thumb_row[6],
                    "cache_hit": True,
                }
        # else: cache miss or stale — regenerate
    finally:
        conn.close()

    src_abs = _abs_from_repo_relative(filepath)
    if not src_abs.exists():
        return None

    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    thumb_abs = _thumbnail_abs_path(render_id)

    try:
        with Image.open(src_abs) as im:
            # JPEG can't carry alpha or palette modes; convert.
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGB")
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX), Image.Resampling.LANCZOS)
            im.save(thumb_abs, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            width, height = im.size
        bytes_size = thumb_abs.stat().st_size
    except (OSError, ValueError, Image.UnidentifiedImageError):
        # Corrupt file, unsupported format, or unreadable. Don't insert
        # a state.db row — caller treats None as "thumbnail not available."
        return None

    now = _iso_now()
    rel_path = _thumbnail_relative_path(render_id)
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO audit_thumbnails (
                    render_id, thumbnail_path, source_hash, width, height,
                    bytes, created
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(render_id) DO UPDATE SET
                    thumbnail_path = excluded.thumbnail_path,
                    source_hash = excluded.source_hash,
                    width = excluded.width,
                    height = excluded.height,
                    bytes = excluded.bytes,
                    created = excluded.created
                """,
                (render_id, rel_path, canonical_hash,
                 width, height, bytes_size, now),
            )
    finally:
        conn.close()

    return {
        "render_id": render_id,
        "thumbnail_abs_path": thumb_abs,
        "source_hash": canonical_hash,
        "width": width, "height": height,
        "bytes": bytes_size, "created": now,
        "cache_hit": False,
    }


def get_render_abs_path(render_id: str) -> Optional[Path]:
    """Return absolute path to a render's canonical file, or None if
    the render row doesn't exist or the file is missing on disk.
    Used by the /audit/render/{id}/file serve endpoint for full-size
    image display in the serial view.
    """
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT filepath FROM renders WHERE id = ?", (render_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    abs_path = _abs_from_repo_relative(row[0])
    return abs_path if abs_path.exists() else None
