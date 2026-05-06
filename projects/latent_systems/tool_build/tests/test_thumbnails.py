#!/usr/bin/env python3
"""Phase 2 Wave A — audit thumbnail cache tests.

Exercises thumbnails.get_or_generate against synthetic PNGs:
  - generation populates state.db row + writes JPEG file
  - cache hit on identical canonical_hash
  - cache invalidation on canonical_hash change
  - downscale to MAX_EDGE_PX preserves aspect ratio
  - missing render row returns None
  - missing render file returns None

Test prefix: test_thumb_ for renders rows. Test scratch files live at
_data/_test_thumb_renders/ (gitignored per _data/_test_*/ pattern).

Run: python tool_build/tests/test_thumbnails.py
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (Pattern #3: import db for codec setup)
import thumbnails  # noqa: E402


PREFIX = "test_thumb_"
TEST_RENDERS_DIR = db.DATA_DIR / "_test_thumb_renders"


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def _make_test_png(name: str, width: int = 2400, height: int = 1600,
                   color: tuple = (200, 100, 50)) -> Path:
    """Create a synthetic PNG at TEST_RENDERS_DIR/<name>.png. Returns abs path."""
    TEST_RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    abs_path = TEST_RENDERS_DIR / f"{name}.png"
    im = Image.new("RGB", (width, height), color=color)
    im.save(abs_path, format="PNG")
    return abs_path


def _seed_render(render_id: str, abs_png_path: Path, canonical_hash: str) -> None:
    """Insert renders row pointing at the synthetic PNG."""
    repo_root = db.TOOL_BUILD_DIR.parent.parent.parent
    rel_path = abs_png_path.resolve().relative_to(repo_root.resolve()).as_posix()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO renders (
                    id, attempt_id, prompt_id, filename, filepath,
                    download_hash, canonical_hash, tool, variant, hero_status,
                    discipline_version, yaml_path, created
                ) VALUES (?, NULL, NULL, ?, ?, NULL, ?, 'midjourney', NULL,
                          NULL, '1.0', NULL, '2026-05-06T00:00:00+00:00')
                """,
                (render_id, abs_png_path.name, rel_path, canonical_hash),
            )
    finally:
        conn.close()


def _set_canonical_hash(render_id: str, new_hash: str) -> None:
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                "UPDATE renders SET canonical_hash = ? WHERE id = ?",
                (new_hash, render_id),
            )
    finally:
        conn.close()


def cleanup():
    """Clean test rows + test files + test thumbnails."""
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                "DELETE FROM audit_thumbnails WHERE render_id LIKE ?",
                (f"{PREFIX}%",),
            )
            conn.execute(
                "DELETE FROM renders WHERE id LIKE ?", (f"{PREFIX}%",),
            )
    finally:
        conn.close()
    if TEST_RENDERS_DIR.exists():
        shutil.rmtree(TEST_RENDERS_DIR, ignore_errors=True)
    for thumb_path in (db.DATA_DIR / "_audit_thumbnails").glob(f"{PREFIX}*.jpg"):
        thumb_path.unlink(missing_ok=True)


def test_generate_basic():
    """Generation creates JPEG, populates state.db row, downscales correctly."""
    rid = f"{PREFIX}basic"
    src = _make_test_png(rid, width=2400, height=1600)
    _seed_render(rid, src, canonical_hash="hash_basic_v1")

    info = thumbnails.get_or_generate(rid)
    _assert(info is not None, "expected non-None thumbnail info")
    _assert(info["source_hash"] == "hash_basic_v1")
    _assert(info["cache_hit"] is False, "first call should be cache miss")
    _assert(info["thumbnail_abs_path"].exists(), "JPEG file should exist on disk")

    # Downscale: max edge should be MAX_EDGE_PX (1568); aspect preserved.
    # Source 2400x1600 -> 1568x1045 (1568/2400 ratio applied to 1600).
    _assert(max(info["width"], info["height"]) == thumbnails.MAX_EDGE_PX,
            f"max edge should be {thumbnails.MAX_EDGE_PX}, got {info['width']}x{info['height']}")
    aspect_orig = 2400 / 1600
    aspect_thumb = info["width"] / info["height"]
    _assert(abs(aspect_orig - aspect_thumb) < 0.01,
            f"aspect ratio drift: orig={aspect_orig}, thumb={aspect_thumb}")

    # State.db row populated
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT source_hash, width, height FROM audit_thumbnails WHERE render_id = ?",
            (rid,),
        ).fetchone()
    finally:
        conn.close()
    _assert(row is not None and row[0] == "hash_basic_v1")
    _assert(row[1] == info["width"] and row[2] == info["height"])


def test_cache_hit_on_unchanged_hash():
    """Second call with same canonical_hash returns cache_hit=True."""
    rid = f"{PREFIX}cache_hit"
    src = _make_test_png(rid, width=400, height=400)
    _seed_render(rid, src, canonical_hash="hash_unchanged")

    info1 = thumbnails.get_or_generate(rid)
    _assert(info1 is not None and info1["cache_hit"] is False)
    info2 = thumbnails.get_or_generate(rid)
    _assert(info2 is not None and info2["cache_hit"] is True,
            "second call should be cache hit")


def test_cache_invalidation_on_hash_change():
    """When renders.canonical_hash changes, next call regenerates."""
    rid = f"{PREFIX}invalidate"
    src = _make_test_png(rid, width=400, height=300)
    _seed_render(rid, src, canonical_hash="hash_v1")

    info1 = thumbnails.get_or_generate(rid)
    _assert(info1 is not None and info1["cache_hit"] is False)
    _assert(info1["source_hash"] == "hash_v1")

    # Simulate canonical change
    _set_canonical_hash(rid, "hash_v2")

    info2 = thumbnails.get_or_generate(rid)
    _assert(info2 is not None,
            "expected regeneration after hash change, got None")
    _assert(info2["cache_hit"] is False,
            "post-invalidation call should be cache miss")
    _assert(info2["source_hash"] == "hash_v2",
            f"thumbnail should record new hash: got {info2['source_hash']}")


def test_no_downscale_when_already_small():
    """Sources smaller than MAX_EDGE_PX stay at their native size."""
    rid = f"{PREFIX}small"
    src = _make_test_png(rid, width=512, height=384)
    _seed_render(rid, src, canonical_hash="hash_small")

    info = thumbnails.get_or_generate(rid)
    _assert(info is not None)
    # Pillow's thumbnail() preserves size when already within bounds.
    _assert(info["width"] == 512 and info["height"] == 384,
            f"small image should stay {(512, 384)}, got {info['width']}x{info['height']}")


def test_missing_render_returns_none():
    """get_or_generate on a render_id not in state.db returns None."""
    info = thumbnails.get_or_generate(f"{PREFIX}does_not_exist")
    _assert(info is None, f"expected None for missing render, got {info!r}")


def test_missing_file_returns_none():
    """Render row exists but file is missing on disk -> None."""
    rid = f"{PREFIX}missing_file"
    src = _make_test_png(rid)
    _seed_render(rid, src, canonical_hash="hash_missing")
    src.unlink()  # delete the file

    info = thumbnails.get_or_generate(rid)
    _assert(info is None,
            f"expected None for missing file, got {info!r}")


def test_get_render_abs_path():
    """get_render_abs_path returns absolute path for existing rendered file."""
    rid = f"{PREFIX}get_abs"
    src = _make_test_png(rid)
    _seed_render(rid, src, canonical_hash="hash_get_abs")
    abs_path = thumbnails.get_render_abs_path(rid)
    _assert(abs_path is not None)
    _assert(abs_path.exists())
    _assert(abs_path.resolve() == src.resolve())

    # Non-existent render -> None
    _assert(thumbnails.get_render_abs_path(f"{PREFIX}ghost") is None)


def main():
    cleanup()
    try:
        test_generate_basic()
        test_cache_hit_on_unchanged_hash()
        test_cache_invalidation_on_hash_change()
        test_no_downscale_when_already_small()
        test_missing_render_returns_none()
        test_missing_file_returns_none()
        test_get_render_abs_path()
    finally:
        cleanup()
    print("PASS: thumbnails — generate, cache-hit, invalidation, "
          "downscale, missing-render, missing-file, render-abs-path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
