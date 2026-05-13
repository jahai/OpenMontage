#!/usr/bin/env python3
"""Rough-cut player backend tests (Day 3 of Phase 3 sprint).

Covers roughcut.build_roughcut_data + helpers. Scenarios per spec
acceptance (min 4-6 across data-derivation paths):

  1. Full pipeline: section with hero_zone + strong renders + audio
     → assets sequenced by verdict_created ASC, narration paragraph-
     ordered, timing_strategy='narration_distributed'.
  2. Renders only (no audio): section matched, 3s/image fallback,
     no_narration banner present.
  3. Audio only (no matched renders): empty assets, no_assets banner
     present.
  4. weak/reject filter: weak + reject verdicts excluded from assets.
  5. Section alias normalization: h3_skinner alias matches H3 filename
     pattern AND concept.section='h3_skinner' row both surface.
  6. MAX(discipline_version): two versions in db, query returns only
     rows at the max version.
  7. No data at all: empty assets + audio, both banners present.
  8. Asset type classification: video extensions → 'video', else
     'image'.

Run via pytest (fixture-isolated DB). Standalone `python tests/test_roughcut.py`
also works.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (Pattern #3)
import roughcut  # noqa: E402


PREFIX = "test_rc_"


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def cleanup():
    db.cascading_delete(PREFIX)


def _iso(offset_seconds: float = 0.0) -> str:
    return (datetime.now(timezone.utc) +
            timedelta(seconds=offset_seconds)).isoformat()


def _seed_concept(*, suffix: str, section: str) -> str:
    cid = f"{PREFIX}c_{suffix}"
    now = _iso()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """INSERT INTO concepts
                   (id, name, ep, section, subject, register, status,
                    discipline_version, yaml_path, created, modified)
                   VALUES (?, ?, 'ep1', ?, 't', 'schematic_apparatus',
                           'drafting', '1.0', '_test', ?, ?)""",
                (cid, f"{PREFIX}n_{suffix}", section, now, now),
            )
    finally:
        conn.close()
    return cid


def _seed_render_with_verdict(
    *, suffix: str, concept_id: Optional[str] = None,
    filename: Optional[str] = None,
    verdict_value: str = "strong",
    verdict_offset_seconds: float = 0.0,
    tool: str = "midjourney",
) -> tuple[str, str]:
    """Insert render + (optional) prompt + verdict. Returns (render_id, verdict_id)."""
    rid = f"{PREFIX}r_{suffix}"
    vid = f"{PREFIX}v_{suffix}"
    prompt_id = f"{PREFIX}p_{suffix}" if concept_id else None
    fn = filename or f"{rid}.png"
    now = _iso()
    conn = db.connect()
    try:
        with conn:
            if prompt_id and concept_id:
                conn.execute(
                    """INSERT INTO prompts
                       (id, concept_id, tool, text_preview, status,
                        drafted_by, discipline_version, yaml_path, created)
                       VALUES (?, ?, ?, 't', 'completed', 'manual',
                               '1.0', '_test', ?)""",
                    (prompt_id, concept_id, tool, now),
                )
            conn.execute(
                """INSERT INTO renders
                   (id, attempt_id, prompt_id, filename, filepath,
                    download_hash, canonical_hash, tool, variant,
                    hero_status, discipline_version, yaml_path, created)
                   VALUES (?, NULL, ?, ?, ?, NULL, ?, ?, NULL, NULL,
                           '1.0', '_test', ?)""",
                (rid, prompt_id, fn,
                 f"projects/latent_systems/_test/{fn}",
                 f"h_{rid}", tool, now),
            )
            conn.execute(
                """INSERT INTO verdicts
                   (id, render_id, rubric_used, verdict, audited_by,
                    rubric_version, flags_needs_second_look,
                    discipline_version, yaml_path, created)
                   VALUES (?, ?, 't', ?, 'human', '1.0', 0,
                           '1.0', '_test', ?)""",
                (vid, rid, verdict_value, _iso(verdict_offset_seconds)),
            )
    finally:
        conn.close()
    return rid, vid


def _seed_audio_asset(
    *, suffix: str, section_label: str, paragraph_number: int,
    variant_label: str = "X20_take1",
    discipline_version: str = "1.4",
    is_canonical: bool = False,
) -> str:
    aid = f"{PREFIX}a_{suffix}"
    now = _iso()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """INSERT INTO audio_assets
                   (id, filepath, filename, section_label,
                    paragraph_number, variant_label, voice_profile,
                    discipline_version, duration_seconds, canonical_hash,
                    is_canonical, yaml_path, created, modified)
                   VALUES (?, ?, ?, ?, ?, ?, 'radio_news_host', ?,
                           NULL, ?, ?, '_test', ?, ?)""",
                (aid,
                 f"projects/latent_systems/_test_audio/{aid}.mp3",
                 f"{aid}.mp3",
                 section_label, paragraph_number, variant_label,
                 discipline_version, f"h_{aid}",
                 1 if is_canonical else 0,
                 now, now),
            )
    finally:
        conn.close()
    return aid


# Need to import this AFTER the seed functions since they reference it.
from typing import Optional  # noqa: E402


def main() -> int:
    cleanup()

    # ---- Test 1: full pipeline (renders + audio) ----
    print("Test 1: full pipeline — section with hero_zone + strong + audio")
    c1 = _seed_concept(suffix="s17", section="section_17")
    _seed_render_with_verdict(
        suffix="r1", concept_id=c1, verdict_value="hero_zone",
        verdict_offset_seconds=10,
    )
    _seed_render_with_verdict(
        suffix="r2", concept_id=c1, verdict_value="strong",
        verdict_offset_seconds=20,
    )
    _seed_audio_asset(
        suffix="a1", section_label="section_17", paragraph_number=1,
    )
    _seed_audio_asset(
        suffix="a2", section_label="section_17", paragraph_number=2,
    )
    data = roughcut.build_roughcut_data("ep1", "section_17")
    _assert(data["section"] == "section_17")
    _assert(data["has_assets"] is True, f"expected has_assets=True: {data['has_assets']}")
    _assert(data["has_narration"] is True)
    _assert(data["asset_count"] == 2, f"expected 2 assets, got {data['asset_count']}")
    _assert(data["narration_count"] == 2)
    _assert(data["timing_strategy"] == "narration_distributed")
    _assert(data["audio_discipline_version"] == "1.4")
    _assert(data["banners"] == [])
    # Asset order: verdict_created ASC → r1 (offset 10) before r2 (offset 20)
    _assert(data["assets"][0]["id"] == f"{PREFIX}r_r1")
    _assert(data["assets"][1]["id"] == f"{PREFIX}r_r2")
    # Narration order: paragraph 1 before 2
    _assert(data["narration_audios"][0]["paragraph_number"] == 1)
    _assert(data["narration_audios"][1]["paragraph_number"] == 2)
    print(f"  {data['asset_count']} assets, {data['narration_count']} audios, "
          f"version={data['audio_discipline_version']}, "
          f"strategy={data['timing_strategy']}")
    cleanup()

    # ---- Test 2: renders only (no audio) — 3s fallback + banner ----
    print("\nTest 2: renders only — 3s/image fallback, no_narration banner")
    c2 = _seed_concept(suffix="h3", section="h3_skinner")
    _seed_render_with_verdict(
        suffix="r3", concept_id=c2, verdict_value="hero_zone",
    )
    data = roughcut.build_roughcut_data("ep1", "h3_skinner")
    _assert(data["has_assets"] is True)
    _assert(data["has_narration"] is False)
    _assert(data["timing_strategy"] == "default_3s_per_image")
    _assert(data["default_image_duration"] == 3.0)
    no_narr = [b for b in data["banners"] if b["kind"] == "no_narration"]
    _assert(len(no_narr) == 1, f"expected no_narration banner: {data['banners']}")
    print("  fallback to 3s/image; no_narration banner present")
    cleanup()

    # ---- Test 3: audio only (no matched renders) — banner ----
    print("\nTest 3: audio only — empty assets, no_assets banner")
    _seed_audio_asset(
        suffix="a3", section_label="section_18", paragraph_number=1,
    )
    data = roughcut.build_roughcut_data("ep1", "section_18")
    _assert(data["has_assets"] is False)
    _assert(data["has_narration"] is True)
    _assert(data["asset_count"] == 0)
    no_assets = [b for b in data["banners"] if b["kind"] == "no_assets"]
    _assert(len(no_assets) == 1, "expected no_assets banner")
    print("  empty assets; no_assets banner present")
    cleanup()

    # ---- Test 4: weak/reject excluded ----
    print("\nTest 4: weak + reject verdicts excluded from assets")
    c4 = _seed_concept(suffix="s19", section="section_19")
    _seed_render_with_verdict(
        suffix="weak1", concept_id=c4, verdict_value="weak",
    )
    _seed_render_with_verdict(
        suffix="rej1", concept_id=c4, verdict_value="reject",
    )
    _seed_render_with_verdict(
        suffix="ok1", concept_id=c4, verdict_value="strong",
    )
    data = roughcut.build_roughcut_data("ep1", "section_19")
    _assert(data["asset_count"] == 1, f"expected only 1 strong asset, got {data['asset_count']}")
    _assert(data["assets"][0]["verdict"] == "strong")
    print(f"  filtered: 1 strong kept; weak + reject dropped")
    cleanup()

    # ---- Test 5: alias normalization (h3_skinner ↔ H3) ----
    print("\nTest 5: alias normalization — h3_skinner matches both concept "
          "section and H3 filename pattern")
    c5 = _seed_concept(suffix="h3b", section="h3_skinner")
    # Render via concept (concept.section = 'h3_skinner')
    _seed_render_with_verdict(
        suffix="byconc", concept_id=c5, verdict_value="strong",
        filename="byconcept.png",
    )
    # Render via filename only (no concept; filename 'EP1_H3_xxx')
    _seed_render_with_verdict(
        suffix="byfn", concept_id=None, verdict_value="strong",
        filename="EP1_H3_lab_wide_v2.png",
        verdict_offset_seconds=5,
    )
    # Render in DIFFERENT section ('h5_slot_machine') — should NOT match
    c5b = _seed_concept(suffix="h5", section="h5_slot_machine")
    _seed_render_with_verdict(
        suffix="other", concept_id=c5b, verdict_value="strong",
    )
    data = roughcut.build_roughcut_data("ep1", "h3_skinner")
    _assert(data["asset_count"] == 2,
            f"expected 2 (concept-bound + filename-matched), got {data['asset_count']}")
    ids = {a["id"] for a in data["assets"]}
    _assert(f"{PREFIX}r_byconc" in ids)
    _assert(f"{PREFIX}r_byfn" in ids)
    _assert(f"{PREFIX}r_other" not in ids,
            "h5_slot_machine render should NOT match h3_skinner section")
    # Aliases include both forms
    _assert("h3_skinner" in data["section_aliases"])
    _assert("H3" in data["section_aliases"])
    print(f"  matched both concept-bound + filename-matched; rejected other section")
    cleanup()

    # ---- Test 6: MAX(discipline_version) ----
    print("\nTest 6: MAX(discipline_version) — query returns latest version only")
    _seed_audio_asset(
        suffix="v10", section_label="section_20", paragraph_number=1,
        discipline_version="1.0",
    )
    _seed_audio_asset(
        suffix="v14", section_label="section_20", paragraph_number=1,
        discipline_version="1.4",
    )
    data = roughcut.build_roughcut_data("ep1", "section_20")
    _assert(data["audio_discipline_version"] == "1.4",
            f"expected 1.4 (max), got {data['audio_discipline_version']}")
    _assert(data["narration_count"] == 1,
            f"should return 1 audio at v1.4, got {data['narration_count']}")
    print(f"  picked max version 1.4; rejected v1.0 row")
    cleanup()

    # ---- Test 7: no data at all — both banners ----
    print("\nTest 7: no data — both no_assets + no_narration banners present")
    data = roughcut.build_roughcut_data("ep1", "section_does_not_exist")
    _assert(data["has_assets"] is False)
    _assert(data["has_narration"] is False)
    _assert(data["asset_count"] == 0)
    _assert(data["narration_count"] == 0)
    kinds = {b["kind"] for b in data["banners"]}
    _assert("no_assets" in kinds)
    _assert("no_narration" in kinds)
    print(f"  both banners present; empty-state payload returned")
    cleanup()

    # ---- Test 8: asset type classification ----
    print("\nTest 8: asset type classification — video vs image extensions")
    c8 = _seed_concept(suffix="vid", section="h4_video")
    _seed_render_with_verdict(
        suffix="img1", concept_id=c8, verdict_value="strong",
        filename="EP1_H4_still.png",
    )
    _seed_render_with_verdict(
        suffix="vid1", concept_id=c8, verdict_value="strong",
        filename="EP1_H4_clip.mp4", tool="kling",
        verdict_offset_seconds=5,
    )
    data = roughcut.build_roughcut_data("ep1", "h4_video")
    types = {a["asset_type"] for a in data["assets"]}
    _assert("image" in types)
    _assert("video" in types)
    img_assets = [a for a in data["assets"] if a["asset_type"] == "image"]
    vid_assets = [a for a in data["assets"] if a["asset_type"] == "video"]
    _assert(len(img_assets) == 1)
    _assert(len(vid_assets) == 1)
    _assert(vid_assets[0]["filename"].endswith(".mp4"))
    print(f"  classified: 1 image + 1 video; mixed-asset section works")
    cleanup()

    # ---- Test 9: get_audio_asset_by_id helper ----
    print("\nTest 9: get_audio_asset_by_id lookup")
    aid = _seed_audio_asset(
        suffix="lookup", section_label="section_99", paragraph_number=1,
    )
    rec = roughcut.get_audio_asset_by_id(aid)
    _assert(rec is not None)
    _assert(rec["id"] == aid)
    _assert(rec["section_label"] == "section_99")
    missing = roughcut.get_audio_asset_by_id("nonexistent_id")
    _assert(missing is None)
    print(f"  lookup returns record; nonexistent ID returns None")
    cleanup()

    print("\nPASS: all roughcut behaviors verified")
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_roughcut.py`
    invocation remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
