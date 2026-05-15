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

    # ---- Test 10: HTTP endpoint renders the template cleanly ----
    print("\nTest 10: HTTP endpoint renders roughcut_player template")
    from fastapi.testclient import TestClient
    import app as app_module
    client = TestClient(app_module.app)
    # Seed a minimal section the player can render against.
    c10 = _seed_concept(suffix="http", section="section_http")
    _seed_render_with_verdict(
        suffix="http_r", concept_id=c10, verdict_value="strong",
    )
    response = client.get("/video/ep1/section/section_http/roughcut")
    _assert(response.status_code == 200,
            f"expected 200, got {response.status_code}: {response.text[:200]}")
    body = response.text
    _assert("Rough cut: section_http" in body,
            "expected section header in rendered template")
    _assert("player-stage" in body, "expected player-stage element")
    _assert("Asset 1 of 1" in body or "Asset" in body,
            "expected current-asset label")
    # Banner for no narration should be present
    _assert("no-narration" in body or "Narration not yet recorded" in body,
            "expected no_narration banner")

    # Data endpoint mirror
    data_resp = client.get("/video/ep1/section/section_http/roughcut/data")
    _assert(data_resp.status_code == 200)
    payload = data_resp.json()
    _assert(payload["asset_count"] == 1)
    _assert(payload["has_narration"] is False)

    # /audio_assets/{id}/file: 404 for missing
    missing_resp = client.get("/audio_assets/does_not_exist/file")
    _assert(missing_resp.status_code == 404)
    print("  endpoint renders 200; data endpoint mirrors; 404 on missing audio")

    # Day 4 polish: template carries scrub-bar + thumb-strip + overrides row.
    _assert('id="scrub-bar"' in body, "expected scrub bar element")
    _assert('id="thumb-strip"' in body, "expected thumb strip element")
    _assert('save-overrides-btn' in body, "expected save overrides button")
    _assert('INTER_PARAGRAPH_GAP_SECONDS = 0.5' in body,
            "expected default gap constant injected (Q4 default)")
    print("  Day 4 polish elements present: scrub-bar, thumb-strip, save button, gap=0.5")
    cleanup()

    # ---- Test 11: overrides GET/POST + apply_overrides integration ----
    print("\nTest 11: overrides GET/POST endpoints + payload integration")
    import rough_cut_overrides
    OVERRIDE_SECTION = "section_overrides_test"
    # Wipe any leftover sidecar from prior runs.
    sidecar_path = rough_cut_overrides._overrides_path(OVERRIDE_SECTION)
    if sidecar_path.exists():
        sidecar_path.unlink()

    # Seed two renders so we can reorder + duration-override.
    c11 = _seed_concept(suffix="ovr", section=OVERRIDE_SECTION)
    r11a = _seed_render_with_verdict(
        suffix="ovr_a", concept_id=c11, verdict_value="hero_zone",
    )
    r11b = _seed_render_with_verdict(
        suffix="ovr_b", concept_id=c11, verdict_value="strong",
    )

    # GET on no-overrides section returns {} and default gap surfaces in player.
    resp = client.get(
        f"/video/ep1/section/{OVERRIDE_SECTION}/roughcut/overrides"
    )
    _assert(resp.status_code == 200)
    _assert(resp.json() == {}, f"expected empty dict, got {resp.json()}")
    data = client.get(
        f"/video/ep1/section/{OVERRIDE_SECTION}/roughcut/data"
    ).json()
    _assert(data["inter_paragraph_gap_seconds"] == 0.5,
            f"expected default 0.5s gap, got {data['inter_paragraph_gap_seconds']}")
    _assert(data["overrides_present"] is False)
    natural_order = [a["id"] for a in data["assets"]]
    _assert(len(natural_order) == 2, f"expected 2 assets, got {natural_order}")

    # POST overrides — reverse the asset order + custom gap + per-asset duration.
    reversed_order = list(reversed(natural_order))
    post_resp = client.post(
        f"/video/ep1/section/{OVERRIDE_SECTION}/roughcut/overrides",
        json={
            "manual_sequence": reversed_order,
            "per_asset_duration_seconds": {natural_order[0]: 7.5},
            "inter_paragraph_gap_seconds": 0.3,
        },
    )
    _assert(post_resp.status_code == 200)
    saved = post_resp.json()
    _assert(saved["saved"] is True)
    _assert(saved["overrides"]["manual_sequence"] == reversed_order)

    # Re-fetch player data — overrides must be reflected.
    data2 = client.get(
        f"/video/ep1/section/{OVERRIDE_SECTION}/roughcut/data"
    ).json()
    applied_order = [a["id"] for a in data2["assets"]]
    _assert(applied_order == reversed_order,
            f"expected applied order {reversed_order}, got {applied_order}")
    _assert(data2["inter_paragraph_gap_seconds"] == 0.3,
            f"expected 0.3s, got {data2['inter_paragraph_gap_seconds']}")
    _assert(data2["overrides_present"] is True)
    overridden_asset = next(
        a for a in data2["assets"] if a["id"] == natural_order[0]
    )
    _assert(overridden_asset.get("override_duration_seconds") == 7.5,
            f"expected 7.5s override, got {overridden_asset.get('override_duration_seconds')}")

    # Cleanup the test sidecar so production directory stays clean.
    if sidecar_path.exists():
        sidecar_path.unlink()
    print("  GET empty -> default gap; POST persists; data endpoint reflects overrides")
    cleanup()

    # ---- Test 12: build_roughcut_full_data chains sections ----
    print("\nTest 12: build_roughcut_full_data concatenates sections")
    cleanup()
    # Seed two sections, each with a render + verdict.
    s1 = "section_full_a"
    s2 = "section_full_b"
    c12a = _seed_concept(suffix="full_a", section=s1)
    c12b = _seed_concept(suffix="full_b", section=s2)
    _seed_render_with_verdict(
        suffix="full_a_r", concept_id=c12a, verdict_value="hero_zone",
    )
    _seed_render_with_verdict(
        suffix="full_b_r", concept_id=c12b, verdict_value="strong",
    )
    full = roughcut.build_roughcut_full_data("ep1")
    section_ids = [s["section"] for s in full["sections"]]
    _assert(s1 in section_ids and s2 in section_ids,
            f"both seeded sections should appear, got {section_ids}")
    _assert(full["asset_count"] >= 2,
            f"expected >=2 chained assets, got {full['asset_count']}")
    boundaries = full["section_boundaries"]
    _assert(len(boundaries) >= 2,
            f"expected boundaries for both sections, got {boundaries}")
    # Boundary asset_idx is monotonically nondecreasing.
    asset_idxs = [b["asset_idx"] for b in boundaries]
    _assert(asset_idxs == sorted(asset_idxs),
            f"boundaries must be in order, got {asset_idxs}")
    print(f"  chained {len(full['sections'])} sections, "
          f"{full['asset_count']} combined assets, "
          f"{len(boundaries)} boundary markers")

    # ---- Test 13: episode_overrides section_order honored ----
    print("\nTest 13: episode_overrides section_order overrides discovery default")
    import rough_cut_overrides
    EP_TEST = "ep_full_order_test"
    # Seed concepts for this fake episode so discovery has something — but
    # use the SAME sections to control test scope cleanly.
    rough_cut_overrides.save_episode_overrides(
        EP_TEST, {"section_order": [s2, s1]},
    )
    full_ordered = roughcut.build_roughcut_full_data(EP_TEST)
    _assert(full_ordered["section_order"] == [s2, s1],
            f"expected explicit order [{s2}, {s1}], got {full_ordered['section_order']}")
    # Sections list reflects that order.
    ordered_ids = [s["section"] for s in full_ordered["sections"]]
    _assert(ordered_ids == [s2, s1],
            f"expected sections in [{s2}, {s1}] order, got {ordered_ids}")
    # Cleanup episode override file.
    ep_path = rough_cut_overrides._episode_overrides_path(EP_TEST)
    if ep_path.exists():
        ep_path.unlink()
    _assert(full_ordered["overrides_present"] is True)
    print(f"  episode-override section_order respected: {ordered_ids}")

    # ---- Test 14: HTTP endpoint /video/{ep}/roughcut_full renders ----
    print("\nTest 14: HTTP /roughcut_full endpoint renders + lists sections")
    full_resp = client.get("/video/ep1/roughcut_full")
    _assert(full_resp.status_code == 200,
            f"expected 200, got {full_resp.status_code}: {full_resp.text[:200]}")
    body14 = full_resp.text
    _assert("Full-episode rough cut" in body14)
    _assert(s1 in body14 or s2 in body14,
            "expected at least one seeded section in chained view")
    _assert("scrub-bar" in body14)
    # Data endpoint mirror
    data14 = client.get("/video/ep1/roughcut_full/data").json()
    _assert("section_boundaries" in data14)
    _assert("section_order" in data14)
    print("  endpoint renders 200; data endpoint mirrors; section list visible")
    cleanup()

    # ---- Test 15: regression — multiple positive verdicts on one render dedupe ----
    # Production render a1e9b7a81079e6d2 surfaced this in the Day 4 smoke test:
    # 5 separate hero_zone/strong verdicts (re-grading over time, supersedes
    # not always set) JOIN-multiplied into 5 duplicate asset entries. Dedup
    # via window function keeps the latest verdict per render.
    print("\nTest 15: render with multiple hero_zone/strong verdicts dedupes to one asset")
    DEDUP_SECTION = "section_dedup_test"
    c15 = _seed_concept(suffix="dedup", section=DEDUP_SECTION)
    r15, _v15 = _seed_render_with_verdict(
        suffix="dedup", concept_id=c15, verdict_value="hero_zone",
        verdict_offset_seconds=-30,
    )
    # Stack two newer verdicts on the SAME render, distinct verdict ids.
    # Latest one ("strong" at offset 0) should be what surfaces.
    conn_dedup = db.connect()
    try:
        with conn_dedup:
            conn_dedup.execute(
                """INSERT INTO verdicts
                   (id, render_id, rubric_used, verdict, audited_by,
                    rubric_version, flags_needs_second_look,
                    discipline_version, yaml_path, created)
                   VALUES (?, ?, 't', ?, 'human', '1.0', 0,
                           '1.0', '_test', ?)""",
                (f"{PREFIX}v_dedup_mid", r15, "hero_zone", _iso(-15)),
            )
            conn_dedup.execute(
                """INSERT INTO verdicts
                   (id, render_id, rubric_used, verdict, audited_by,
                    rubric_version, flags_needs_second_look,
                    discipline_version, yaml_path, created)
                   VALUES (?, ?, 't', ?, 'human', '1.0', 0,
                           '1.0', '_test', ?)""",
                (f"{PREFIX}v_dedup_latest", r15, "strong", _iso(0)),
            )
    finally:
        conn_dedup.close()

    data15 = roughcut.build_roughcut_data("ep1", DEDUP_SECTION)
    assets15 = data15["assets"]
    _assert(len(assets15) == 1,
            f"expected 1 deduped asset, got {len(assets15)} "
            f"(render {r15} has 3 positive verdicts)")
    _assert(assets15[0]["id"] == r15)
    # Window function picks ROW_NUMBER=1 = MAX(created) — latest verdict wins.
    _assert(assets15[0]["verdict"] == "strong",
            f"latest verdict should surface; got {assets15[0]['verdict']}")
    print(f"  3 verdicts on 1 render -> 1 asset; latest verdict ({assets15[0]['verdict']}) surfaces")
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
