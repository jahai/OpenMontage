#!/usr/bin/env python3
"""Audio asset first-class state.db support tests (Day 2 of Phase 3 sprint).

Covers audio_assets.py: parse_audio_filename, ingest_audio_file,
rebuild_audio_cache, get_audio_assets_for_section, set_canonical_variant.

Project-specific looks-like-target-but-isn't cases (Pattern #8 third
bucket): load-bearing validation files don't match the canonical
section_para pattern; archived/_DEPRECATED_ paths are skipped; the
walker doesn't confuse them.

Run via pytest (fixture-isolated DB). Standalone `python tests/test_audio_assets.py`
also works but touches production paths.
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (Pattern #3: import db for codec setup)
import audio_assets  # noqa: E402


PREFIX = "test_audio_"


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def cleanup():
    """Best-effort. Under pytest fixture, tmp_path auto-cleans."""
    db.cascading_delete(PREFIX)


def _write_test_mp3(rel_path: str, contents: bytes = b"fake-mp3-bytes") -> Path:
    """Create a synthetic mp3 file under db.REPO_ROOT at the given rel_path."""
    abs_path = db.REPO_ROOT / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(contents)
    return abs_path


def _write_test_wav(rel_path: str, duration_seconds: float = 1.0) -> Path:
    """Create a real silent WAV file. mutagen supports WAV natively, so the
    probe path can be exercised end-to-end without needing a real MP3
    fixture (constructing valid MP3 frame headers manually is fragile)."""
    abs_path = db.REPO_ROOT / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    framerate = 8000
    nframes = int(framerate * duration_seconds)
    with wave.open(str(abs_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(b"\x00\x00" * nframes)
    return abs_path


def main() -> int:
    cleanup()

    # ===== parse_audio_filename =====

    print("Test 1: parse canonical filename with period_hack")
    r = audio_assets.parse_audio_filename(
        "EP1_section_17_para_1_radio_news_host_X20_periodhack_take2.mp3"
    )
    _assert(r is not None, "should match canonical pattern")
    _assert(r["section_label"] == "section_17")
    _assert(r["paragraph_number"] == 1)
    _assert(r["voice_profile"] == "radio_news_host")
    _assert(r["x_value"] == 20)
    _assert(r["has_period_hack"] is True)
    _assert(r["take_number"] == 2)
    _assert(r["variant_label"] == "X20_periodhack_take2")
    print("  parsed: section_17/p1/radio_news_host/X20_periodhack_take2")

    print("\nTest 2: parse canonical filename without period_hack")
    r = audio_assets.parse_audio_filename(
        "EP1_section_17_para_5_radio_news_host_X22_take1.mp3"
    )
    _assert(r is not None)
    _assert(r["has_period_hack"] is False)
    _assert(r["variant_label"] == "X22_take1")
    print("  parsed: no period_hack")

    print("\nTest 3: parse rejects load-bearing validation filename")
    r = audio_assets.parse_audio_filename(
        "EP1_loadbearing_8_radio_news_host_X24_take1.mp3"
    )
    _assert(r is None, "load-bearing filenames should not match canonical pattern")
    print("  rejected (load-bearing has separate schema)")

    print("\nTest 4: parse rejects random filename")
    r = audio_assets.parse_audio_filename("random_file.mp3")
    _assert(r is None)
    r = audio_assets.parse_audio_filename(
        "EP1_section_17_para_1_radio_news_host_X20_periodhack_take2.wav"
    )
    _assert(r is None, "non-.mp3 extension should reject")
    print("  random + wrong-extension both rejected")

    # ===== ingest_audio_file =====

    print("\nTest 5: ingest single audio file (insert)")
    rel_path = (
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/"
        "EP1_section_17_para_1_radio_news_host_X20_periodhack_take2.mp3"
    )
    abs_path = _write_test_mp3(rel_path, contents=b"first-version")
    result = audio_assets.ingest_audio_file(
        abs_path,
        _id_override=f"{PREFIX}p1",
    )
    _assert(result["action"] == "inserted", f"expected inserted, got {result['action']}")
    _assert(result["section_label"] == "section_17")
    _assert(result["paragraph_number"] == 1)
    _assert(result["discipline_version"] == "1.4",
            f"expected version 1.4 from path, got {result['discipline_version']}")
    print(f"  inserted; discipline_version extracted from path: {result['discipline_version']}")

    print("\nTest 6: ingest same file again returns 'unchanged'")
    result = audio_assets.ingest_audio_file(
        abs_path, _id_override=f"{PREFIX}p1",
    )
    _assert(result["action"] == "unchanged",
            f"expected unchanged, got {result['action']}")
    print("  idempotent")

    print("\nTest 7: ingest after content change returns 'updated'")
    abs_path.write_bytes(b"second-version-different-hash")
    result = audio_assets.ingest_audio_file(
        abs_path, _id_override=f"{PREFIX}p1",
    )
    _assert(result["action"] == "updated",
            f"expected updated, got {result['action']}")
    print("  updated on hash change")

    # ===== rebuild_audio_cache =====

    print("\nTest 8: rebuild_audio_cache walks canonical tree")
    # Add 2 more files in the same voice dir.
    _write_test_mp3(
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/"
        "EP1_section_17_para_2_radio_news_host_X20_periodhack_take2.mp3"
    )
    _write_test_mp3(
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/"
        "EP1_section_17_para_3_radio_news_host_X24_periodhack_take1.mp3"
    )
    # Add a non-canonical-filename file (load-bearing) — should be skipped.
    _write_test_mp3(
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/load_bearing_validation/"
        "EP1_loadbearing_8_radio_news_host_X24_take1.mp3"
    )
    # Add an archived file — should be skipped via _DEPRECATED_ path filter.
    _write_test_mp3(
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/"
        "_DEPRECATED_old_take/"
        "EP1_section_17_para_1_radio_news_host_X20_take1.mp3"
    )
    summary = audio_assets.rebuild_audio_cache(verbose=False)
    # 4 files walked; 2 new inserts (paragraphs 2 + 3), 1 unchanged
    # (paragraph 1 from Test 7 update), 1 skipped (load-bearing was in
    # load_bearing_validation/ subdir which isn't filtered out by path
    # but its filename doesn't match canonical pattern → skipped_filename).
    # The _DEPRECATED_ file is skipped via path filter.
    _assert(summary["walked"] >= 3,
            f"walked count too low: {summary['walked']}")
    _assert(summary["inserted"] >= 2,
            f"expected >=2 new inserts, got {summary['inserted']}")
    _assert(summary["skipped_filename"] >= 1,
            f"load-bearing should be skipped: {summary}")
    _assert(summary["skipped_archived"] >= 1,
            f"_DEPRECATED_ should be archived-skipped: {summary}")
    print(f"  walked: {summary['walked']}, inserted: {summary['inserted']}, "
          f"unchanged: {summary['unchanged']}, skipped_filename: "
          f"{summary['skipped_filename']}, skipped_archived: "
          f"{summary['skipped_archived']}")

    # ===== get_audio_assets_for_section =====

    print("\nTest 9: get_audio_assets_for_section returns paragraph-ordered")
    rows = audio_assets.get_audio_assets_for_section("section_17")
    _assert(len(rows) >= 3, f"expected >=3 rows for section_17, got {len(rows)}")
    paragraphs = [r["paragraph_number"] for r in rows]
    _assert(paragraphs == sorted(paragraphs),
            f"rows should be paragraph-ordered, got {paragraphs}")
    print(f"  {len(rows)} variants for section_17, paragraph-ordered: {paragraphs}")

    print("\nTest 10: get_audio_assets_for_section(canonical_only=True) "
          "returns nothing before any is_canonical set")
    rows = audio_assets.get_audio_assets_for_section(
        "section_17", canonical_only=True,
    )
    _assert(rows == [], "no canonical variants set yet — should be empty")
    print("  empty (no canonical variants set yet)")

    # ===== set_canonical_variant =====

    print("\nTest 11: set_canonical_variant marks variant exclusively")
    audio_assets.set_canonical_variant(
        section_label="section_17",
        paragraph_number=1,
        variant_label="X20_periodhack_take2",
    )
    rows = audio_assets.get_audio_assets_for_section(
        "section_17", canonical_only=True,
    )
    _assert(len(rows) == 1, f"expected 1 canonical, got {len(rows)}")
    _assert(rows[0]["paragraph_number"] == 1)
    _assert(rows[0]["variant_label"] == "X20_periodhack_take2")
    print(f"  canonical set: p{rows[0]['paragraph_number']}/"
          f"{rows[0]['variant_label']}")

    print("\nTest 12: set_canonical_variant unknown variant refused")
    try:
        audio_assets.set_canonical_variant(
            section_label="section_17",
            paragraph_number=99,  # no para 99
            variant_label="X99_take9",
        )
        _assert(False, "unknown variant should have been refused")
    except ValueError as e:
        _assert("no audio_asset row" in str(e))
    print("  refused with no-row error")

    # ===== Day 4: _probe_duration_seconds + backfill_durations =====

    print("\nTest 13: _probe_duration_seconds returns None on bad bytes")
    bad_path = _write_test_mp3(
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/"
        f"EP1_section_17_para_4_radio_news_host_X22_take1.mp3",
        contents=b"not-a-real-mp3",
    )
    duration = audio_assets._probe_duration_seconds(bad_path)
    _assert(duration is None,
            f"synthetic bytes should probe to None, got {duration!r}")
    print("  None on synthetic bytes (graceful)")

    print("\nTest 14: _probe_duration_seconds returns float on real audio")
    wav_path = _write_test_wav(
        "projects/latent_systems/tool_build/_data/test_fixtures/"
        f"{PREFIX}probe_target.wav",
        duration_seconds=1.0,
    )
    duration = audio_assets._probe_duration_seconds(wav_path)
    _assert(duration is not None,
            "real WAV should probe to a duration")
    _assert(0.95 <= duration <= 1.05,
            f"expected ~1.0s, got {duration:.3f}s")
    print(f"  probed {duration:.3f}s for 1.0s WAV (mutagen end-to-end)")

    print("\nTest 15: ingest_audio_file writes NULL duration when probe fails")
    rel_path_15 = (
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/"
        "EP1_section_17_para_5_radio_news_host_X22_take1.mp3"
    )
    abs_path_15 = _write_test_mp3(rel_path_15, contents=b"still-not-real-mp3")
    result = audio_assets.ingest_audio_file(
        abs_path_15, _id_override=f"{PREFIX}p5",
    )
    _assert(result["action"] == "inserted")
    _assert(result["duration_seconds"] is None,
            f"probe-failed insert should leave duration NULL, "
            f"got {result['duration_seconds']!r}")
    rows = audio_assets.get_audio_assets_for_section("section_17")
    p5 = next((r for r in rows if r["paragraph_number"] == 5), None)
    _assert(p5 is not None and p5["duration_seconds"] is None,
            "state.db should reflect NULL duration_seconds for synthetic ingest")
    print("  NULL duration persisted; probe failure is non-fatal")

    print("\nTest 16: backfill_durations counts probe_failed for synthetic rows")
    summary = audio_assets.backfill_durations()
    _assert(summary["scanned"] >= 1,
            f"expected to scan synthetic-byte rows, got {summary['scanned']}")
    _assert(summary["probe_failed"] >= 1,
            f"expected probe_failed for synthetic rows, got {summary}")
    _assert(summary["backfilled"] == 0,
            f"no real audio in fixtures, expected 0 backfilled, got {summary}")
    print(f"  scanned={summary['scanned']} probe_failed="
          f"{summary['probe_failed']} backfilled={summary['backfilled']}")

    print("\nTest 17: backfill_durations counts file_missing when file gone")
    # Insert a row whose file we then remove, simulating filesystem drift.
    rel_path_17 = (
        "projects/latent_systems/ep1/audio/v1_4_radio_news_host/section_17/"
        "EP1_section_17_para_6_radio_news_host_X22_take1.mp3"
    )
    abs_path_17 = _write_test_mp3(rel_path_17, contents=b"will-be-deleted")
    audio_assets.ingest_audio_file(
        abs_path_17, _id_override=f"{PREFIX}p6",
    )
    abs_path_17.unlink()
    summary = audio_assets.backfill_durations()
    _assert(summary["file_missing"] >= 1,
            f"expected file_missing for unlinked file, got {summary}")
    print(f"  file_missing={summary['file_missing']} (filesystem drift survives)")

    print("\nTest 18: rebuild_audio_cache summary includes backfill keys")
    summary = audio_assets.rebuild_audio_cache(verbose=False)
    for key in ("backfill_scanned", "backfill_filled",
                "backfill_probe_failed", "backfill_file_missing"):
        _assert(key in summary,
                f"summary missing backfill key {key!r}: {summary}")
    print(f"  rebuild summary surfaces backfill counts: "
          f"scanned={summary['backfill_scanned']} "
          f"filled={summary['backfill_filled']} "
          f"probe_failed={summary['backfill_probe_failed']} "
          f"file_missing={summary['backfill_file_missing']}")

    print("\nPASS: all audio_assets behaviors verified")
    cleanup()
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_audio_assets.py`
    invocation remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
