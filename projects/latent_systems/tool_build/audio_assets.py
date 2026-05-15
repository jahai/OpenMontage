"""Audio asset first-class state.db support (Day 2 of Phase 3 sprint).

Prereq for rough-cut player (Days 4-5). The rough-cut player needs to
query "give me all audio for section_17, paragraph-ordered, with
duration each" — that's not possible at filesystem-walk speed during
playback. audio_assets table + this module provide the indexed-query
substrate.

Filename schema (per project memory v1.4 §13 canonical):
    EP1_section_<N>_para_<P>_<voice_profile>_X<value>[_periodhack]_take<N>.mp3

Examples:
    EP1_section_17_para_1_radio_news_host_X20_periodhack_take2.mp3
    EP1_section_17_para_5_radio_news_host_X22_take1.mp3
    EP1_section_16_para_3_radio_news_host_X24_take1.mp3

Canonical path layout:
    ep1/audio/v<discipline_version>_<voice_profile>/section_<N>/<filename>

Module responsibilities:
  - parse_audio_filename(): regex parse the canonical filename into
    structured fields. Returns None for non-matching filenames so the
    walker can skip them (load-bearing validation files have a separate
    pattern; deferred to Phase 3.5+).
  - ingest_audio_file(): insert one audio_assets row + write YAML
    sidecar. Pattern #7: accepts _id_override for testing.
  - rebuild_audio_cache(): walk the canonical audio tree, ingest every
    matching file. Idempotent (skips already-cataloged files by hash).
  - get_audio_assets_for_section(): query rows for the rough-cut
    player's playlist construction.

NOT in scope for Day 2:
  - Duration probing (requires ffprobe or audio library; deferred to
    Day 4-5 when the player actually needs it).
  - is_canonical resolution (which variant the player plays for a
    section/paragraph). Deferred to Day 4-5; for now all rows land
    with is_canonical=0.
  - Load-bearing validation file pattern. Deferred.
  - Archived / _DEPRECATED_ path handling. Walker enumeration ignores
    these paths.

Pattern #3 import: importing db runs setup_console_encoding so
standalone invocation tolerates non-ASCII glyphs in print statements.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import mutagen
import yaml

import db
from constants import CURRENT_DISCIPLINE_VERSION


# Canonical filename pattern. Anchored to start/end so partial matches
# (e.g., truncated names from manual renames) don't sneak through.
#
# Capture groups:
#   1. section_number      — 1-3 digits
#   2. paragraph_number    — 1-3 digits
#   3. voice_profile       — alphanumeric + underscores; e.g. "radio_news_host"
#   4. x_value             — 1-3 digits (Style Exaggeration)
#   5. periodhack_marker   — "_periodhack" or empty
#   6. take_number         — 1-3 digits
_AUDIO_FILENAME_PATTERN = re.compile(
    r"^EP1_section_(\d{1,3})_para_(\d{1,3})_([a-zA-Z][a-zA-Z0-9_]*?)_"
    r"X(\d{1,3})(_periodhack)?_take(\d{1,3})\.mp3$"
)

# Canonical path pattern for extracting discipline_version from path.
# Canonical layout: ep1/audio/v<X>_<Y>_<voice_profile>/section_<N>/<filename>
# discipline_version is the "X_Y" between "v" and the voice_profile.
_AUDIO_PATH_VERSION_PATTERN = re.compile(
    r"/ep1/audio/v(\d+)_(\d+)_[a-zA-Z][a-zA-Z0-9_]*?/section_\d+/"
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audio_asset_id_from(filepath_rel: str) -> str:
    """Derive a stable 16-char hex ID from the repo-relative filepath.
    Pattern #7: _id_override on ingest_audio_file for tests."""
    return hashlib.sha256(filepath_rel.encode("utf-8")).hexdigest()[:16]


def _file_canonical_hash(abs_path: Path) -> str:
    """SHA256 of the file's contents (full hash, not truncated). Used
    for change detection — re-ingest only re-writes the row if hash
    differs from the previous canonical_hash."""
    h = hashlib.sha256()
    with abs_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe_duration_seconds(abs_path: Path) -> Optional[float]:
    """Probe an audio file's duration in seconds via mutagen.

    Returns None on any probe failure (corrupt file, unsupported format,
    synthetic test bytes, missing frames). Callers treat None as "duration
    not yet known"; the row stays at NULL and a later backfill_durations()
    pass can re-attempt once the file is real.

    Day 4 of Phase 3 sprint — scrub bar UI requires server-known total
    duration; relying on client-side HTML5 audio.duration on load (Day 3
    behavior) creates a flicker before total is known and breaks
    pixel-math for click-to-jump.
    """
    try:
        f = mutagen.File(str(abs_path))
    except Exception:
        return None
    if f is None or f.info is None:
        return None
    length = getattr(f.info, "length", None)
    if length is None:
        return None
    try:
        return float(length)
    except (TypeError, ValueError):
        return None


def parse_audio_filename(filename: str) -> Optional[dict]:
    """Parse a canonical audio filename into structured fields.

    Returns None if the filename doesn't match the canonical pattern.
    Callers (walker) should skip non-matching files rather than treat
    them as errors — load-bearing validation files + future variants
    have different naming schemes.

    Returns a dict on success:
        {
            "section_label": "section_17",
            "paragraph_number": 1,
            "voice_profile": "radio_news_host",
            "variant_label": "X20_periodhack_take2",
            "x_value": 20,
            "has_period_hack": True,
            "take_number": 2,
        }
    """
    m = _AUDIO_FILENAME_PATTERN.match(filename)
    if m is None:
        return None
    section_num, para_num, voice_profile, x_val, periodhack, take_num = m.groups()
    has_period_hack = bool(periodhack)
    variant_label = f"X{x_val}{'_periodhack' if has_period_hack else ''}_take{take_num}"
    return {
        "section_label": f"section_{section_num}",
        "paragraph_number": int(para_num),
        "voice_profile": voice_profile,
        "variant_label": variant_label,
        "x_value": int(x_val),
        "has_period_hack": has_period_hack,
        "take_number": int(take_num),
    }


def _extract_discipline_version_from_path(filepath_rel: str) -> Optional[str]:
    """Extract discipline_version from canonical path like
    `projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/...`
    → "1.4". Returns None if path doesn't match canonical layout."""
    m = _AUDIO_PATH_VERSION_PATTERN.search("/" + filepath_rel)
    if m is None:
        return None
    return f"{m.group(1)}.{m.group(2)}"


def _audio_assets_yaml_dir() -> Path:
    return db.DATA_DIR / "audio_assets"


def _write_audio_asset_yaml(record: dict) -> None:
    """Write audio_asset YAML sidecar via tmp + atomic rename."""
    yaml_path = _audio_assets_yaml_dir() / f"{record['id']}.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = yaml_path.with_suffix(yaml_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, sort_keys=False,
                       default_flow_style=False, allow_unicode=True)
    tmp.replace(yaml_path)


def ingest_audio_file(
    abs_path: Path,
    *,
    repo_root: Optional[Path] = None,
    _id_override: Optional[str] = None,  # FOR TESTING ONLY (Pattern #7)
) -> dict:
    """Insert one audio_assets row + write YAML sidecar.

    Idempotent: if a row already exists at this filepath with the same
    canonical_hash, returns the existing row dict unchanged. If the
    hash differs, updates the row.

    Raises ValueError if filename doesn't match the canonical pattern
    (caller should pre-filter via parse_audio_filename if walking a
    mixed directory).
    """
    if repo_root is None:
        repo_root = db.REPO_ROOT

    parsed = parse_audio_filename(abs_path.name)
    if parsed is None:
        raise ValueError(
            f"filename {abs_path.name!r} doesn't match canonical audio "
            f"pattern; cannot ingest"
        )

    filepath_rel = abs_path.resolve().relative_to(repo_root.resolve()).as_posix()
    discipline_version = (
        _extract_discipline_version_from_path(filepath_rel)
        or CURRENT_DISCIPLINE_VERSION
    )

    asset_id = _id_override or _audio_asset_id_from(filepath_rel)
    canonical_hash = _file_canonical_hash(abs_path)
    duration_seconds = _probe_duration_seconds(abs_path)
    yaml_rel = (
        f"projects/latent_systems/tool_build/_data/audio_assets/"
        f"{asset_id}.yaml"
    )
    now = _iso_now()

    conn = db.connect()
    try:
        existing = conn.execute(
            "SELECT id, canonical_hash FROM audio_assets WHERE filepath = ?",
            (filepath_rel,),
        ).fetchone()
        if existing is not None and existing[1] == canonical_hash:
            # Already-cataloged + content unchanged — idempotent return.
            row = conn.execute(
                "SELECT * FROM audio_assets WHERE id = ?", (existing[0],),
            ).fetchone()
            col_names = [c[0] for c in conn.execute(
                "SELECT * FROM audio_assets LIMIT 0").description]
            return {"action": "unchanged", **dict(zip(col_names, row))}
        with conn:
            if existing is not None:
                # Hash changed — update existing row (re-probe duration).
                conn.execute(
                    """UPDATE audio_assets
                          SET canonical_hash = ?,
                              duration_seconds = ?,
                              modified = ?
                        WHERE id = ?""",
                    (canonical_hash, duration_seconds, now, existing[0]),
                )
                action = "updated"
                asset_id = existing[0]
            else:
                conn.execute(
                    """INSERT INTO audio_assets (
                           id, filepath, filename, section_label,
                           paragraph_number, variant_label, voice_profile,
                           discipline_version, duration_seconds,
                           canonical_hash, is_canonical,
                           yaml_path, created, modified
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                    (asset_id, filepath_rel, abs_path.name,
                     parsed["section_label"], parsed["paragraph_number"],
                     parsed["variant_label"], parsed["voice_profile"],
                     discipline_version, duration_seconds, canonical_hash,
                     yaml_rel, now, now),
                )
                action = "inserted"
    finally:
        conn.close()

    record = {
        "id": asset_id,
        "filepath": filepath_rel,
        "filename": abs_path.name,
        "section_label": parsed["section_label"],
        "paragraph_number": parsed["paragraph_number"],
        "variant_label": parsed["variant_label"],
        "voice_profile": parsed["voice_profile"],
        "discipline_version": discipline_version,
        "duration_seconds": duration_seconds,
        "canonical_hash": canonical_hash,
        "is_canonical": 0,
        "yaml_path": yaml_rel,
        "created": now,
        "modified": now,
    }
    _write_audio_asset_yaml(record)
    return {"action": action, **record}


def backfill_durations(
    *, repo_root: Optional[Path] = None, verbose: bool = False,
) -> dict:
    """Probe duration_seconds for any audio_assets row where it's NULL.

    Day 4 of Phase 3 sprint — covers two cases the per-ingest probe can't:
      - Pre-mutagen rows ingested before _probe_duration_seconds existed
      - Rows where the original ingest probe failed (transient I/O, file
        replaced after first ingest, etc.) and the file is now valid

    Idempotent: probes only NULL-duration rows; rows already populated
    are skipped. Updates state.db column + rewrites YAML sidecar so the
    reproducibility artifact stays in lockstep.

    Returns summary {scanned, backfilled, probe_failed, file_missing}.
    """
    if repo_root is None:
        repo_root = db.REPO_ROOT
    summary = {
        "scanned": 0, "backfilled": 0,
        "probe_failed": 0, "file_missing": 0,
    }
    conn = db.connect()
    try:
        rows = conn.execute(
            """SELECT id, filepath, filename, section_label,
                      paragraph_number, variant_label, voice_profile,
                      discipline_version, canonical_hash, is_canonical,
                      yaml_path, created
               FROM audio_assets
               WHERE duration_seconds IS NULL"""
        ).fetchall()
        col_names = (
            "id", "filepath", "filename", "section_label",
            "paragraph_number", "variant_label", "voice_profile",
            "discipline_version", "canonical_hash", "is_canonical",
            "yaml_path", "created",
        )
        for row in rows:
            summary["scanned"] += 1
            r = dict(zip(col_names, row))
            abs_path = repo_root / r["filepath"]
            if not abs_path.exists():
                summary["file_missing"] += 1
                if verbose:
                    print(f"[audio backfill] missing file: {r['filepath']}")
                continue
            duration = _probe_duration_seconds(abs_path)
            if duration is None:
                summary["probe_failed"] += 1
                if verbose:
                    print(f"[audio backfill] probe failed: {r['filepath']}")
                continue
            now = _iso_now()
            with conn:
                conn.execute(
                    "UPDATE audio_assets SET duration_seconds = ?, "
                    "modified = ? WHERE id = ?",
                    (duration, now, r["id"]),
                )
            record = {**r, "duration_seconds": duration,
                      "is_canonical": bool(r["is_canonical"]),
                      "modified": now}
            _write_audio_asset_yaml(record)
            summary["backfilled"] += 1
            if verbose:
                print(
                    f"[audio backfill] {r['section_label']}/p"
                    f"{r['paragraph_number']}/{r['variant_label']}: "
                    f"{duration:.3f}s"
                )
    finally:
        conn.close()
    return summary


def rebuild_audio_cache(
    *, repo_root: Optional[Path] = None, verbose: bool = False,
) -> dict:
    """Walk the canonical audio tree and ingest every matching file.

    Idempotent. Skips non-matching filenames (load-bearing validation
    files, archived files, future variant schemes). Skips files under
    `archive/` or `_DEPRECATED_*/` path fragments.

    Day 4 of Phase 3 sprint: calls backfill_durations() at end so any
    pre-mutagen NULL-duration rows get populated in the same pass.

    Returns a summary dict for caller reporting.
    """
    if repo_root is None:
        repo_root = db.REPO_ROOT

    audio_root = (
        repo_root / "projects" / "latent_systems" / "ep1" / "audio"
    )
    summary = {
        "walked": 0, "inserted": 0, "updated": 0,
        "unchanged": 0, "skipped_filename": 0,
        "skipped_archived": 0, "errors": 0,
    }
    if not audio_root.exists():
        if verbose:
            print(f"[audio] no audio tree at {audio_root}; nothing to walk")
        return summary

    # Walk only canonical voice-profile dirs: v<X>_<Y>_<voice>/section_*/
    for voice_dir in sorted(audio_root.iterdir()):
        if not voice_dir.is_dir():
            continue
        if not voice_dir.name.startswith("v"):
            # archive/, load_bearing_validation/, etc. — skip non-canonical
            summary["skipped_archived"] += sum(
                1 for _ in voice_dir.rglob("*.mp3")
            )
            continue
        for mp3_path in voice_dir.rglob("*.mp3"):
            summary["walked"] += 1
            # Skip archived/deprecated paths within the canonical voice dir.
            path_parts = mp3_path.relative_to(voice_dir).parts
            if any(p.startswith(("_DEPRECATED_", "archive")) for p in path_parts):
                summary["skipped_archived"] += 1
                continue
            if parse_audio_filename(mp3_path.name) is None:
                summary["skipped_filename"] += 1
                if verbose:
                    print(f"[audio] skip non-canonical filename: {mp3_path.name}")
                continue
            try:
                result = ingest_audio_file(mp3_path, repo_root=repo_root)
                summary[result["action"]] += 1
                if verbose and result["action"] in ("inserted", "updated"):
                    print(
                        f"[audio] {result['action']}: "
                        f"{result['section_label']}/p{result['paragraph_number']}/"
                        f"{result['variant_label']}"
                    )
            except Exception as e:
                summary["errors"] += 1
                if verbose:
                    print(f"[audio] ERROR ingesting {mp3_path.name}: {e}")

    backfill = backfill_durations(repo_root=repo_root, verbose=verbose)
    summary["backfill_scanned"] = backfill["scanned"]
    summary["backfill_filled"] = backfill["backfilled"]
    summary["backfill_probe_failed"] = backfill["probe_failed"]
    summary["backfill_file_missing"] = backfill["file_missing"]
    return summary


def get_audio_assets_for_section(
    section_label: str,
    *,
    canonical_only: bool = False,
) -> list[dict]:
    """Query audio assets for a section, paragraph-ordered.

    For rough-cut player playlist construction (Days 4-5 of sprint):
    `get_audio_assets_for_section("section_17", canonical_only=True)`
    returns the canonical variant for each paragraph in playback order.

    With `canonical_only=False` (default), returns all variants — for
    UI surfaces that let Joseph pick which variant is canonical.
    """
    conn = db.connect()
    try:
        if canonical_only:
            sql = """
                SELECT id, filepath, filename, section_label,
                       paragraph_number, variant_label, voice_profile,
                       discipline_version, duration_seconds,
                       canonical_hash, is_canonical, yaml_path,
                       created, modified
                FROM audio_assets
                WHERE section_label = ? AND is_canonical = 1
                ORDER BY paragraph_number ASC, variant_label ASC
            """
        else:
            sql = """
                SELECT id, filepath, filename, section_label,
                       paragraph_number, variant_label, voice_profile,
                       discipline_version, duration_seconds,
                       canonical_hash, is_canonical, yaml_path,
                       created, modified
                FROM audio_assets
                WHERE section_label = ?
                ORDER BY paragraph_number ASC, variant_label ASC
            """
        rows = conn.execute(sql, (section_label,)).fetchall()
        col_names = (
            "id", "filepath", "filename", "section_label",
            "paragraph_number", "variant_label", "voice_profile",
            "discipline_version", "duration_seconds", "canonical_hash",
            "is_canonical", "yaml_path", "created", "modified",
        )
        return [dict(zip(col_names, r)) for r in rows]
    finally:
        conn.close()


def set_canonical_variant(
    *,
    section_label: str,
    paragraph_number: int,
    variant_label: str,
) -> dict:
    """Mark one variant as the canonical pick for (section, paragraph).

    Clears `is_canonical` on any other variants for the same
    (section, paragraph) — exactly one canonical per slot.
    """
    conn = db.connect()
    try:
        with conn:
            # Clear existing canonical flag for this slot.
            conn.execute(
                """UPDATE audio_assets
                      SET is_canonical = 0, modified = ?
                    WHERE section_label = ? AND paragraph_number = ?
                      AND is_canonical = 1""",
                (_iso_now(), section_label, paragraph_number),
            )
            # Set new canonical.
            cur = conn.execute(
                """UPDATE audio_assets
                      SET is_canonical = 1, modified = ?
                    WHERE section_label = ? AND paragraph_number = ?
                      AND variant_label = ?""",
                (_iso_now(), section_label, paragraph_number, variant_label),
            )
            if cur.rowcount == 0:
                raise ValueError(
                    f"no audio_asset row for section_label={section_label!r}, "
                    f"paragraph_number={paragraph_number}, "
                    f"variant_label={variant_label!r}"
                )
    finally:
        conn.close()
    return {
        "ok": True,
        "section_label": section_label,
        "paragraph_number": paragraph_number,
        "variant_label": variant_label,
    }
