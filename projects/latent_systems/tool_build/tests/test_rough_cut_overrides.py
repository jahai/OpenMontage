#!/usr/bin/env python3
"""rough_cut_overrides module tests (Day 4 of Phase 3 sprint).

Covers load_overrides, save_overrides, apply_overrides — per-section
YAML sidecar persistence + override application logic for the rough-cut
player.

Per Joseph's Q2 confirmation (2026-05-14): YAML sidecar approach. Tests
namespace section IDs with PREFIX so the test fixtures don't collide
with real per-section override files.

Run via pytest (fixture-isolated DB; YAML files in _data/ are cleaned at
end of main()). Standalone `python tests/test_rough_cut_overrides.py`
also works.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (Pattern #3: import db for codec setup)
import rough_cut_overrides  # noqa: E402


PREFIX = "test_rco_"


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def cleanup():
    """Remove any test YAML sidecars under _data/rough_cut_overrides/."""
    overrides_dir = rough_cut_overrides._overrides_dir()
    if overrides_dir.exists():
        for p in overrides_dir.glob(f"{PREFIX}*.yaml"):
            p.unlink()


def _make_asset(asset_id: str, asset_type: str = "image") -> dict:
    return {"id": asset_id, "filepath": f"path/{asset_id}.png",
            "asset_type": asset_type, "verdict": "hero_zone"}


def main() -> int:
    cleanup()

    print("Test 1: load_overrides returns {} when file doesn't exist")
    section = f"{PREFIX}nonexistent"
    overrides = rough_cut_overrides.load_overrides(section)
    _assert(overrides == {},
            f"missing file should give empty dict, got {overrides}")
    print("  empty dict on missing file")

    print("\nTest 2: save_overrides + load_overrides round-trip")
    section = f"{PREFIX}roundtrip"
    payload = {
        "manual_sequence": ["a", "b", "c"],
        "per_asset_duration_seconds": {"a": 2.5, "b": 4.0},
        "inter_paragraph_gap_seconds": 0.7,
    }
    rough_cut_overrides.save_overrides(section, payload)
    loaded = rough_cut_overrides.load_overrides(section)
    _assert(loaded == payload,
            f"round-trip mismatch: saved {payload}, loaded {loaded}")
    print("  round-trip preserves all fields")

    print("\nTest 3: apply_overrides with empty dict returns assets + default gap")
    assets = [_make_asset("a"), _make_asset("b")]
    result, gap = rough_cut_overrides.apply_overrides(assets, {})
    _assert(result == assets,
            "empty overrides should leave assets unchanged")
    _assert(gap == rough_cut_overrides.DEFAULT_INTER_PARAGRAPH_GAP_SECONDS,
            f"expected default gap, got {gap}")
    _assert(gap == 0.5, f"default gap should be 0.5 (Q4), got {gap}")
    print(f"  assets unchanged; gap defaults to {gap}s")

    print("\nTest 4: apply_overrides with manual_sequence reorders assets")
    assets = [_make_asset("a"), _make_asset("b"), _make_asset("c")]
    result, _ = rough_cut_overrides.apply_overrides(
        assets, {"manual_sequence": ["c", "a", "b"]},
    )
    ids = [a["id"] for a in result]
    _assert(ids == ["c", "a", "b"], f"expected reorder c,a,b, got {ids}")
    print(f"  reordered: {ids}")

    print("\nTest 5: apply_overrides drops unknown IDs in sequence gracefully")
    assets = [_make_asset("a"), _make_asset("b")]
    result, _ = rough_cut_overrides.apply_overrides(
        assets, {"manual_sequence": ["b", "ghost_id", "a"]},
    )
    ids = [a["id"] for a in result]
    _assert(ids == ["b", "a"], f"expected b,a (ghost dropped), got {ids}")
    print(f"  ghost ID skipped: {ids}")

    print("\nTest 6: apply_overrides appends leftovers when sequence is partial")
    # New asset 'c' was promoted after sequence was last edited — must NOT
    # disappear; should land at end of player.
    assets = [_make_asset("a"), _make_asset("b"), _make_asset("c")]
    result, _ = rough_cut_overrides.apply_overrides(
        assets, {"manual_sequence": ["b", "a"]},
    )
    ids = [a["id"] for a in result]
    _assert(ids == ["b", "a", "c"],
            f"new asset c should append at end, got {ids}")
    print(f"  partial sequence appends new assets: {ids}")

    print("\nTest 7: apply_overrides stamps override_duration_seconds")
    assets = [_make_asset("a"), _make_asset("b")]
    result, _ = rough_cut_overrides.apply_overrides(
        assets, {"per_asset_duration_seconds": {"a": 3.5}},
    )
    a = next(x for x in result if x["id"] == "a")
    b = next(x for x in result if x["id"] == "b")
    _assert(a.get("override_duration_seconds") == 3.5,
            f"a should have override 3.5, got {a.get('override_duration_seconds')}")
    _assert("override_duration_seconds" not in b,
            f"b should NOT have override, got {b}")
    print(f"  a.override_duration_seconds={a['override_duration_seconds']}; b unstamped")

    print("\nTest 8: apply_overrides returns inter_paragraph_gap_seconds when set")
    assets = [_make_asset("a")]
    _, gap = rough_cut_overrides.apply_overrides(
        assets, {"inter_paragraph_gap_seconds": 0.3},
    )
    _assert(gap == 0.3, f"expected 0.3, got {gap}")
    print(f"  custom gap returned: {gap}s")

    print("\nTest 9: save_overrides creates parent dir on first write")
    section = f"{PREFIX}first_write"
    # Ensure path doesn't exist by inspecting dir freshly
    rough_cut_overrides.save_overrides(section, {"manual_sequence": ["x"]})
    _assert(rough_cut_overrides._overrides_path(section).exists(),
            "file should exist after save")
    print("  parent dir auto-created")

    print("\nTest 10: save_overrides leaves no .tmp files behind")
    section = f"{PREFIX}atomic"
    rough_cut_overrides.save_overrides(
        section, {"inter_paragraph_gap_seconds": 0.6},
    )
    tmp_files = list(rough_cut_overrides._overrides_dir().glob("*.tmp"))
    _assert(tmp_files == [],
            f"expected no .tmp leftovers, found {tmp_files}")
    print("  atomic rename clean (no .tmp leftovers)")

    print("\nPASS: all rough_cut_overrides behaviors verified")
    cleanup()
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
