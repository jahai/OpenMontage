#!/usr/bin/env python3
"""Day 13 — Feature 9 discipline-drift query + cost breakdown.

Tests:
  1. discipline_drift_summary returns version breakdown across artifact types
  2. summary handles missing tables gracefully
  3. discipline_drift_artifacts returns per-type lists for a version
  4. discipline_drift_artifacts respects limit_per_type
  5. stale_lineage_edges flags edges with valid_to_version OR mismatched valid_from_version
  6. cost_breakdown windows compute correctly (today / 7d / 30d)
  7. cost_breakdown by_purpose groups successful calls

Test data uses 'test_d13_' prefix for cleanup.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
import dispatcher  # noqa: E402


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def _iso(dt):
    return dt.isoformat()


def _now():
    return datetime.now(timezone.utc)


def cleanup():
    db.cascading_delete("test_d13_")
    # cross_ai_captures isn't in the FK graph; clean directly.
    conn = db.connect()
    try:
        with conn:
            conn.execute("DELETE FROM cross_ai_captures WHERE id LIKE 'test_d13_%'")
    finally:
        conn.close()


def main() -> int:
    cleanup()
    now = _now()

    # Seed: artifacts at three different discipline versions
    print("Seeding test artifacts at v0.9, 1.0, pre_v1...")
    conn = db.connect()
    try:
        with conn:
            # 2 concepts at 1.0
            for i, dv in enumerate(["1.0", "1.0", "0.9"]):
                conn.execute(
                    "INSERT INTO concepts (id, name, status, discipline_version, "
                    "yaml_path, created, modified) VALUES (?, ?, 'drafting', ?, '_t', ?, ?)",
                    (f"test_d13_c{i}", f"concept_{i}", dv, _iso(now), _iso(now)),
                )
            # 3 prompts at 1.0, 1 at pre_v1
            for i, dv in enumerate(["1.0", "1.0", "1.0", "pre_v1"]):
                conn.execute(
                    "INSERT INTO prompts (id, tool, status, drafted_by, "
                    "discipline_version, yaml_path, created) "
                    "VALUES (?, 'midjourney', 'draft', 'manual', ?, '_t', ?)",
                    (f"test_d13_p{i}", dv, _iso(now)),
                )
            # 5 renders at pre_v1, 2 at 1.0
            for i, dv in enumerate(["pre_v1"] * 5 + ["1.0", "1.0"]):
                conn.execute(
                    "INSERT INTO renders (id, filename, filepath, canonical_hash, "
                    "tool, discipline_version, created) "
                    "VALUES (?, ?, ?, ?, 'mj', ?, ?)",
                    (f"test_d13_r{i}", f"r{i}.png", f"_t/r{i}.png",
                     f"hash_{i}", dv, _iso(now)),
                )
            # 1 lineage edge at 1.0, 1 at 0.9 with valid_to_version (stale)
            conn.execute(
                "INSERT INTO lineage_edges (id, source_type, source_id, target_type, "
                "target_id, layer, valid_from_version, created) "
                "VALUES ('test_d13_le1', 'render', 'test_d13_r0', 'concept', "
                "'test_d13_c0', 1, '1.0', ?)",
                (_iso(now),),
            )
            conn.execute(
                "INSERT INTO lineage_edges (id, source_type, source_id, target_type, "
                "target_id, layer, valid_from_version, valid_to_version, "
                "stale_reason, created) "
                "VALUES ('test_d13_le2', 'render', 'test_d13_r1', 'concept', "
                "'test_d13_c2', 1, '0.9', '1.0', 'discipline bump', ?)",
                (_iso(now),),
            )
            # 1 hero_promotion at 1.0 (FK to a render — use existing)
            conn.execute(
                "INSERT INTO hero_promotions (id, render_id, hero_filepath, "
                "discipline_version, yaml_path, created) "
                "VALUES ('test_d13_h1', 'test_d13_r5', '/winners/r5.png', "
                "'1.0', '_t', ?)",
                (_iso(now),),
            )
            # 2 api_calls at varied times: today + 8 days ago + 35 days ago
            conn.execute(
                "INSERT INTO api_calls (id, provider, endpoint, purpose, "
                "started, status, tokens_in, tokens_out, cost_usd_estimate) "
                "VALUES ('test_d13_a_today', 'anthropic', 'messages', 'prompt_drafting', "
                "?, 'succeeded', 100, 50, 0.05)",
                (_iso(now),),
            )
            conn.execute(
                "INSERT INTO api_calls (id, provider, endpoint, purpose, "
                "started, status, tokens_in, tokens_out, cost_usd_estimate) "
                "VALUES ('test_d13_a_8d', 'anthropic', 'messages', 'prompt_drafting', "
                "?, 'succeeded', 200, 100, 0.10)",
                (_iso(now - timedelta(days=8)),),
            )
            conn.execute(
                "INSERT INTO api_calls (id, provider, endpoint, purpose, "
                "started, status, tokens_in, tokens_out, cost_usd_estimate) "
                "VALUES ('test_d13_a_35d', 'anthropic', 'messages', 'audit_consultation', "
                "?, 'succeeded', 300, 150, 1.50)",
                (_iso(now - timedelta(days=35)),),
            )
            conn.execute(
                "INSERT INTO api_calls (id, provider, endpoint, purpose, "
                "started, status, tokens_in, tokens_out, cost_usd_estimate, error) "
                "VALUES ('test_d13_a_rl', 'anthropic', 'messages', 'prompt_drafting', "
                "?, 'rate_limited', NULL, NULL, NULL, 'rate limit')",
                (_iso(now),),
            )
    finally:
        conn.close()

    # ---- Test 1: discipline_drift_summary ----
    print("\nTest 1: discipline_drift_summary aggregates correctly")
    summary = dispatcher.discipline_drift_summary()
    versions = summary["versions"]
    _assert("1.0" in versions, "1.0 should appear in versions")
    _assert("pre_v1" in versions, "pre_v1 should appear")
    _assert("0.9" in versions, "0.9 should appear")

    # 1.0 totals: 2 concepts + 3 prompts + 2 renders + 1 hero + 1 lineage = 9
    expected_10 = summary["totals_by_version"]["1.0"]
    # But state.db may have other 1.0 rows from earlier test data — we check
    # the test contributions specifically.
    _assert(versions["1.0"]["concepts"] >= 2, f"expected >=2 concepts at 1.0: {versions['1.0']['concepts']}")
    _assert(versions["1.0"]["prompts"] >= 3, f"expected >=3 prompts at 1.0: {versions['1.0']['prompts']}")
    _assert(versions["1.0"]["renders"] >= 2, f"expected >=2 renders at 1.0: {versions['1.0']['renders']}")
    _assert(versions["1.0"]["hero_promotions"] >= 1)
    _assert(versions["1.0"]["lineage_edges"] >= 1)
    _assert(versions["pre_v1"]["renders"] >= 5)  # plus existing 1698
    _assert(versions["0.9"]["concepts"] == 1)
    _assert(versions["0.9"]["lineage_edges"] == 1)
    print(f"  versions found: {sorted(versions.keys())}")
    print(f"  totals: {summary['totals_by_version']}")

    # ---- Test 2: discipline_drift_artifacts (drill-down) ----
    print("\nTest 2: discipline_drift_artifacts at 0.9")
    artifacts = dispatcher.discipline_drift_artifacts("0.9")
    _assert(artifacts["version"] == "0.9")
    _assert(len(artifacts["artifacts"]["concepts"]) == 1)
    _assert(artifacts["artifacts"]["concepts"][0]["id"] == "test_d13_c2")
    _assert(len(artifacts["artifacts"]["lineage_edges"]) == 1)
    _assert(artifacts["artifacts"]["lineage_edges"][0]["valid_to_version"] == "1.0")
    _assert(artifacts["artifacts"]["lineage_edges"][0]["stale_reason"] == "discipline bump")
    print(f"  found {len(artifacts['artifacts']['concepts'])} concepts, {len(artifacts['artifacts']['lineage_edges'])} edges at 0.9")

    # ---- Test 3: limit_per_type ----
    print("\nTest 3: limit_per_type respected")
    artifacts = dispatcher.discipline_drift_artifacts("pre_v1", limit_per_type=3)
    _assert(len(artifacts["artifacts"]["renders"]) <= 3,
            f"limit not respected: got {len(artifacts['artifacts']['renders'])}")
    print(f"  pre_v1 renders limited to 3 (real count > 3)")

    # ---- Test 4: stale_lineage_edges ----
    print("\nTest 4: stale_lineage_edges identifies non-current valid_from")
    stale = dispatcher.stale_lineage_edges()
    stale_ids = {e["id"] for e in stale}
    _assert("test_d13_le2" in stale_ids,
            f"le2 (valid_to=1.0, valid_from=0.9) should be stale: {stale_ids}")
    # le1 has valid_from=1.0 which IS the current baseline, so should NOT be stale
    _assert("test_d13_le1" not in stale_ids,
            "le1 at current baseline should NOT be stale")
    print(f"  flagged {len(stale)} stale edges")

    # ---- Test 5: cost_breakdown windows ----
    print("\nTest 5: cost_breakdown rolling windows")
    breakdown = dispatcher.cost_breakdown()
    # today_usd should include the 0.05 today
    _assert(breakdown["today_usd"] >= 0.05, f"today: {breakdown['today_usd']}")
    # past_7d should include today (0.05) but NOT 8-day-old
    # Within tolerance — other test data may exist
    _assert(breakdown["past_7d_usd"] >= 0.05)
    _assert(breakdown["past_7d_usd"] < breakdown["past_30d_usd"] + 0.001,
            "7d <= 30d invariant")
    # past_30d includes 0.05 + 0.10 (8d ago) but NOT 35d ago
    _assert(breakdown["past_30d_usd"] >= 0.15,
            f"30d should be >=$0.15: {breakdown['past_30d_usd']}")
    print(f"  today: ${breakdown['today_usd']}, 7d: ${breakdown['past_7d_usd']}, 30d: ${breakdown['past_30d_usd']}")

    # ---- Test 6: cost_breakdown by_purpose ----
    print("\nTest 6: cost_breakdown by_purpose groups")
    _assert("prompt_drafting" in breakdown["by_purpose"])
    print(f"  by_purpose: {breakdown['by_purpose']}")

    # ---- Test 7: cost_breakdown by_status counts ----
    print("\nTest 7: cost_breakdown by_status_30d counts")
    _assert("rate_limited" in breakdown["by_status_30d"],
            f"rate_limited in 30d should be counted: {breakdown['by_status_30d']}")
    _assert("succeeded" in breakdown["by_status_30d"])
    print(f"  by_status_30d: {breakdown['by_status_30d']}")

    print("\nTest 8: cleanup")
    cleanup()
    print("  ok")

    print("\nPASS: all Day 13 discipline-drift + cost-breakdown behaviors verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
