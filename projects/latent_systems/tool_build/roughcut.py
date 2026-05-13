"""Rough-cut player backend (Day 3 of Phase 3 sprint).

Provides `build_roughcut_data(ep_id, section)` returning a dict the
roughcut_player.html template renders into a playable in-app rough cut.

Day 3 v1 scope:
  - Sequencing: fallback only — hero_zone + strong renders bound to
    the section, ordered by verdicts.created ASC. Section binding via
    concepts.section join (when prompt→concept link present) OR
    filename pattern match (parallel to app.video_sections_endpoint).
    EP1_STRUCTURAL_ARCHITECTURE_v1_4.md beat-structure parsing
    deferred to Day 4 polish.
  - Audio query: MAX(discipline_version) per section_label.
    audio_assets.discipline_version is the audio archival namespace
    (1.4 = post-voice-change), NOT the code/spec
    CURRENT_DISCIPLINE_VERSION (1.0 = walker baseline). Column-name
    overload banked as Phase 2.5+ cleanup candidate.
  - Asset timing: narration distributed equally across all assets
    when present; 3s/image fallback when absent. Video assets play
    natural duration (client-side metadata; server returns the
    filepath, no duration probing on Day 3).
  - Gap detection: explicit status banners for missing audio, missing
    assets, missing section data.

Day 4 polish layers on top:
  - EP1_STRUCTURAL_ARCHITECTURE_v1_4.md beat-structure parsing
  - Manual sequence override (rough_cut_overrides table if persistence
    needed)
  - Server-side audio duration probing via mutagen
  - Timeline visualization + scrub-bar
  - Asset thumbnail strip with current-position highlight
  - Side-by-side comparison view
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any, Optional

import db


# Asset timing fallback when no narration audio available.
DEFAULT_IMAGE_DURATION_SECONDS = 3.0

# Render filename patterns for section identification. Parallel to
# app.video_sections_endpoint's patterns; reused so the rough-cut
# player understands the same section namespace the section workspace
# does. Section alias normalization (h3_skinner ↔ H3, section_17 ↔ §17)
# happens in _section_aliases below.
_FILENAME_SECTION_PATTERNS = (
    re.compile(r"^EP1_section_(\d+[A-Z]?)_", re.IGNORECASE),
    re.compile(r"^section_(\d+[A-Z]?)_", re.IGNORECASE),
    re.compile(r"^EP1_(H\d+)[_.]", re.IGNORECASE),
    re.compile(r"^EP1_(K\d+)[_.]", re.IGNORECASE),
    re.compile(r"^(H\d+)[_.]", re.IGNORECASE),
    re.compile(r"^(K\d+)[_.]", re.IGNORECASE),
    re.compile(r"_(H\d+)_", re.IGNORECASE),
    re.compile(r"^EP1_(\d+[A-Z]?)_", re.IGNORECASE),
)

# Video filename extensions (everything else treated as image).
_VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".m4v")


def _extract_section_from_filename(filename: str) -> Optional[str]:
    """Extract a section alias from a render filename, mirroring
    app.video_sections_endpoint's normalization (numeric → §N;
    H/K letter-prefixed → uppercase as-is)."""
    if not filename:
        return None
    for pat in _FILENAME_SECTION_PATTERNS:
        m = pat.search(filename)
        if m:
            tok = m.group(1)
            if tok[0].isdigit():
                return f"§{tok}"  # § + number
            return tok.upper()
    return None


def _section_aliases(section: str) -> list[str]:
    """Return a list of section aliases to match against renders +
    concepts. Handles the three section-naming schemes the codebase
    currently uses:

      - concepts.section style: 'h3_skinner', 'h5_slot_machine'
      - filename-derived numeric: '§17', '§13A'
      - filename-derived H/K: 'H3', 'K1'

    Examples:
      'h3_skinner' → ['h3_skinner', 'H3']
      'section_17' → ['section_17', '§17']
      '§17'        → ['§17']
      'H3'         → ['H3']
    """
    aliases = [section]
    if section.startswith("section_"):
        num = section[len("section_"):]
        aliases.append(f"§{num}")
    elif section[:1].lower() == "h" and len(section) > 1:
        # 'h3_skinner' or 'h3' → 'H3'
        num_part = section[1:].split("_")[0]
        if num_part.isdigit() or (num_part[:-1].isdigit() and num_part[-1].isalpha()):
            aliases.append(f"H{num_part}".upper())
    elif section[:1].lower() == "k" and len(section) > 1:
        num_part = section[1:].split("_")[0]
        if num_part.isdigit():
            aliases.append(f"K{num_part}".upper())
    return aliases


def _classify_asset_type(filepath: str) -> str:
    """Return 'video' for MP4/MOV/WEBM/M4V; 'image' otherwise."""
    return "video" if filepath.lower().endswith(_VIDEO_EXTENSIONS) else "image"


def _query_renders_for_section(
    conn: sqlite3.Connection, section: str,
) -> list[dict]:
    """Return hero_zone + strong renders bound to the section, ordered
    by verdict_created ASC (oldest first = first in sequence per spec).

    Section binding: concepts.section IN aliases OR filename matches
    any alias (mirrors video_sections_endpoint's pattern-matching
    approach). Excludes superseded verdicts.
    """
    aliases = _section_aliases(section)

    # Fetch all candidate hero_zone/strong verdict-having renders;
    # in-Python filter to those matching the section aliases. Avoids a
    # complex WHERE clause that would need to OR concept-section against
    # filename-LIKE patterns. Render count is ~1700 in production; the
    # in-Python pass is cheap enough at that scale.
    rows = conn.execute(
        """
        SELECT r.id, r.filename, r.filepath, r.tool, r.canonical_hash,
               r.hero_status, r.created AS render_created,
               v.id AS verdict_id, v.verdict,
               v.created AS verdict_created,
               c.section AS concept_section
        FROM verdicts v
        JOIN renders r ON r.id = v.render_id
        LEFT JOIN prompts p ON p.id = r.prompt_id
        LEFT JOIN concepts c ON c.id = p.concept_id
        WHERE v.verdict IN ('hero_zone', 'strong')
          AND v.id NOT IN (
              SELECT supersedes_verdict_id FROM verdicts
              WHERE supersedes_verdict_id IS NOT NULL
          )
        ORDER BY v.created ASC
        """
    ).fetchall()

    matched = []
    for row in rows:
        (rid, filename, filepath, tool, canonical_hash, hero_status,
         render_created, verdict_id, verdict_value, verdict_created,
         concept_section) = row
        if concept_section and concept_section in aliases:
            matched.append(row)
            continue
        fn_section = _extract_section_from_filename(filename or "")
        if fn_section and fn_section in aliases:
            matched.append(row)

    return [
        {
            "id": r[0],
            "filename": r[1],
            "filepath": r[2],
            "tool": r[3],
            "canonical_hash": r[4],
            "hero_status": r[5],
            "verdict_id": r[7],
            "verdict": r[8],
            "verdict_created": r[9],
            "concept_section": r[10],
            "asset_type": _classify_asset_type(r[2]),
        }
        for r in matched
    ]


def _query_narration_audios(
    conn: sqlite3.Connection, section: str,
) -> tuple[list[dict], Optional[str]]:
    """Return (narration_audios, audio_discipline_version).

    Audio queried at MAX(discipline_version) for the given
    section_label (exact match — audio uses its own section_label
    namespace; no alias transform on Day 3). When multiple variants
    exist per paragraph, prefer canonical (is_canonical=1); if no
    canonical set, return all variants in (paragraph, variant_label)
    order — the player picks the first per paragraph.

    Returns ([], None) when no audio for the section.
    """
    max_row = conn.execute(
        "SELECT MAX(discipline_version) FROM audio_assets "
        "WHERE section_label = ?",
        (section,),
    ).fetchone()
    if max_row is None or max_row[0] is None:
        return [], None
    max_version = max_row[0]

    # If any canonical variant exists for this section/version, prefer
    # canonical only; otherwise return all variants (player picks first
    # per paragraph). Check existence first.
    canon_count = conn.execute(
        "SELECT COUNT(*) FROM audio_assets "
        "WHERE section_label = ? AND discipline_version = ? "
        "AND is_canonical = 1",
        (section, max_version),
    ).fetchone()[0]

    if canon_count > 0:
        sql = """
            SELECT id, filepath, filename, paragraph_number,
                   variant_label, voice_profile, duration_seconds,
                   is_canonical
            FROM audio_assets
            WHERE section_label = ?
              AND discipline_version = ?
              AND is_canonical = 1
            ORDER BY paragraph_number ASC
        """
    else:
        # No canonical set yet; return all variants — caller picks first
        # per (section, paragraph) slot. paragraph_number NULL last
        # (load-bearing-validation files have no paragraph_number; v1
        # rebuild_audio_cache skips them at filename-pattern level, but
        # leave defensive ordering).
        sql = """
            SELECT id, filepath, filename, paragraph_number,
                   variant_label, voice_profile, duration_seconds,
                   is_canonical
            FROM audio_assets
            WHERE section_label = ?
              AND discipline_version = ?
            ORDER BY (CASE WHEN paragraph_number IS NULL THEN 1 ELSE 0 END),
                     paragraph_number ASC, variant_label ASC
        """

    rows = conn.execute(sql, (section, max_version)).fetchall()

    # Deduplicate to one per paragraph (first wins in the ORDER above).
    seen_paragraphs: set = set()
    deduped: list[dict] = []
    for r in rows:
        para = r[3]
        if para in seen_paragraphs:
            continue
        seen_paragraphs.add(para)
        deduped.append({
            "id": r[0],
            "filepath": r[1],
            "filename": r[2],
            "paragraph_number": para,
            "variant_label": r[4],
            "voice_profile": r[5],
            "duration_seconds": r[6],
            "is_canonical": bool(r[7]),
        })

    return deduped, max_version


def build_roughcut_data(ep_id: str, section: str) -> dict[str, Any]:
    """Build the data payload the roughcut_player template renders.

    Returns:
        {
            "ep_id": str,
            "section": str,
            "section_aliases": list[str],
            "assets": list[dict],                  # sequenced visual assets
            "narration_audios": list[dict],        # paragraph-ordered audio
            "audio_discipline_version": str | None,
            "has_narration": bool,
            "has_assets": bool,
            "asset_count": int,
            "narration_count": int,
            "timing_strategy": str,                # 'narration_distributed' | 'default_3s_per_image'
            "default_image_duration": float,       # 3.0 for fallback
            "banners": list[dict],                 # partial-state messages
        }

    Never raises; returns an empty/banner-only payload when no data
    matches the section. Endpoint layer formats banners into the
    template.
    """
    conn = db.connect()
    try:
        renders = _query_renders_for_section(conn, section)
        audios, audio_version = _query_narration_audios(conn, section)
    finally:
        conn.close()

    has_assets = len(renders) > 0
    has_narration = len(audios) > 0

    banners = []
    if not has_assets:
        banners.append({
            "kind": "no_assets",
            "message": (
                f"No hero-zone or strong renders bound to section "
                f"{section!r} yet. Mark verdicts on renders first, "
                f"or bind renders to a concept whose section matches."
            ),
        })
    if not has_narration:
        banners.append({
            "kind": "no_narration",
            "message": (
                f"Narration not yet recorded for section {section!r} "
                f"(no audio_assets at any discipline_version) — using "
                f"default {DEFAULT_IMAGE_DURATION_SECONDS}s-per-image "
                f"timing."
            ),
        })

    timing_strategy = (
        "narration_distributed" if has_narration else "default_3s_per_image"
    )

    return {
        "ep_id": ep_id,
        "section": section,
        "section_aliases": _section_aliases(section),
        "assets": renders,
        "narration_audios": audios,
        "audio_discipline_version": audio_version,
        "has_narration": has_narration,
        "has_assets": has_assets,
        "asset_count": len(renders),
        "narration_count": len(audios),
        "timing_strategy": timing_strategy,
        "default_image_duration": DEFAULT_IMAGE_DURATION_SECONDS,
        "banners": banners,
    }


def get_audio_asset_by_id(audio_id: str) -> Optional[dict]:
    """Lookup helper for the audio file-serving endpoint.

    Returns the audio_asset row (dict) by primary key, or None if not
    found. Used by /audio_assets/{id}/file to resolve the on-disk path
    before streaming bytes.
    """
    conn = db.connect()
    try:
        row = conn.execute(
            """SELECT id, filepath, filename, section_label,
                      paragraph_number, variant_label, voice_profile,
                      discipline_version, duration_seconds,
                      canonical_hash, is_canonical
               FROM audio_assets WHERE id = ?""",
            (audio_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "id": row[0], "filepath": row[1], "filename": row[2],
        "section_label": row[3], "paragraph_number": row[4],
        "variant_label": row[5], "voice_profile": row[6],
        "discipline_version": row[7],
        "duration_seconds": row[8], "canonical_hash": row[9],
        "is_canonical": bool(row[10]),
    }
