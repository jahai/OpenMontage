#!/usr/bin/env python3
"""Phase 1 acceptance test — success criteria 1, 2, 4 from v1 spec.

This is the formal pass/fail test for Phase 1. Run it before declaring
Phase 1 complete.

Criteria (verbatim from spec):
  1. F1: Prompt-output binding. Given any post-v1 render in canonical
     structure, the prompt that produced it is recoverable by render_id
     query in <2 seconds.
  2. F2: Concept persistence reduces re-derivation tax. Time from "open
     app" to "ready to draft next prompt" <5 minutes (vs current ~1 hour).
  3. F4: Lineage anchoring works for all three layers. Pick a render →
     "what prompts cite this as anchor?" returns list. Pick a prompt →
     "what concepts informed this?" returns list.

This test seeds a synthetic concept→prompt→render→lineage_edge graph,
runs the F1 + F4 queries with timing assertions, and confirms F2 path
exists structurally (UI walkthrough is in ACCEPTANCE.md).

Test data uses 'test_acceptance_' prefix for cleanup.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (importing db runs setup_console_encoding for cp1252 hosts)
import dispatcher  # noqa: E402


F1_BUDGET_SECONDS = 2.0  # spec: "recoverable in <2 seconds"
F2_PATH_REQUIRED_ENDPOINTS = (
    "/concepts",
    "/concepts/{concept_id}",
    "/prompts/draft_via_api",
    "/prompts/{prompt_id}/dispatch",
    "/api_status",
)


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def cleanup():
    db.cascading_delete("test_acceptance_")


def main() -> int:
    cleanup()

    # --- Seed: concept → prompt → render → lineage ---
    print("Seeding synthetic acceptance graph...")
    now = _iso_now()
    conn = db.connect()
    try:
        with conn:
            # Concept C1
            conn.execute(
                "INSERT INTO concepts (id, name, ep, section, subject, register, "
                "status, discipline_version, yaml_path, created, modified) "
                "VALUES ('test_acceptance_c1', 'h5_skinner_box', 'ep1', "
                "'h5_slot_machine', 'rat at slot machine', 'schematic_apparatus', "
                "'evaluated', '1.0', '_t', ?, ?)",
                (now, now),
            )
            # Prompt P1 linked to C1
            conn.execute(
                "INSERT INTO prompts (id, concept_id, tool, text_preview, status, "
                "drafted_by, discipline_version, yaml_path, created) "
                "VALUES ('test_acceptance_p1', 'test_acceptance_c1', 'midjourney', "
                "'rat lab prompt', 'draft', 'claude-opus-4-7', '1.0', '_t', ?)",
                (now,),
            )
            # Render R1 linked to P1
            conn.execute(
                "INSERT INTO renders (id, prompt_id, filename, filepath, "
                "canonical_hash, tool, discipline_version, yaml_path, created) "
                "VALUES ('test_acceptance_r1', 'test_acceptance_p1', 'r1.png', "
                "'_t/r1.png', 'h_r1', 'midjourney', '1.0', '_t', ?)",
                (now,),
            )
            # Render R2 (different) — citing R1 as anchor (lineage layer 1)
            conn.execute(
                "INSERT INTO renders (id, prompt_id, filename, filepath, "
                "canonical_hash, tool, discipline_version, yaml_path, created) "
                "VALUES ('test_acceptance_r2', 'test_acceptance_p1', 'r2.png', "
                "'_t/r2.png', 'h_r2', 'midjourney', '1.0', '_t', ?)",
                (now,),
            )
            # Concept C2 — citing C1 as parent (lineage layer 2)
            conn.execute(
                "INSERT INTO concepts (id, name, status, discipline_version, "
                "yaml_path, created, modified) "
                "VALUES ('test_acceptance_c2', 'h5_slot_machine_alt', 'drafting', "
                "'1.0', '_t', ?, ?)",
                (now, now),
            )
    finally:
        conn.close()

    # Lineage layer 1: R2 → R1 (R2 anchors against R1)
    dispatcher.create_lineage_edge(
        source_type="render", source_id="test_acceptance_r2",
        target_type="render", target_id="test_acceptance_r1",
        layer=1,
    )
    # Lineage layer 2: C2 → C1 (C2 inherits from C1)
    dispatcher.create_lineage_edge(
        source_type="concept", source_id="test_acceptance_c2",
        target_type="concept", target_id="test_acceptance_c1",
        layer=2,
    )

    # --- F1 — Prompt-output binding (recoverable in <2s) ---
    print("\n=== F1 — Prompt-output binding ===")
    print("  Given render_id, recover prompt + concept that produced it")
    t0 = time.perf_counter()
    detail = dispatcher.get_render_detail("test_acceptance_r1")
    elapsed = time.perf_counter() - t0
    _assert(detail is not None, "F1 FAIL: render_detail returned None")
    _assert(detail["prompt"] is not None,
            f"F1 FAIL: post-v1 render missing prompt link: {detail}")
    _assert(detail["prompt"]["id"] == "test_acceptance_p1",
            f"F1 FAIL: wrong prompt: {detail['prompt']['id']}")
    _assert(detail["concept"] is not None,
            f"F1 FAIL: prompt missing concept link: {detail['prompt']}")
    _assert(detail["concept"]["id"] == "test_acceptance_c1",
            f"F1 FAIL: wrong concept: {detail['concept']['id']}")
    _assert(elapsed < F1_BUDGET_SECONDS,
            f"F1 FAIL: query took {elapsed:.3f}s, budget {F1_BUDGET_SECONDS}s")
    print(f"  PASS — recovered prompt + concept in {elapsed*1000:.1f}ms (budget {F1_BUDGET_SECONDS}s)")

    # F1 caveat: pre_v1 renders are unbound (per AD-3) — verify documented limit
    print("\n  AD-3 verification: pre_v1 render returns prompt=None")
    conn = db.connect()
    try:
        pre_v1_id = conn.execute(
            "SELECT id FROM renders WHERE discipline_version='pre_v1' LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if pre_v1_id:
        pre_detail = dispatcher.get_render_detail(pre_v1_id[0])
        _assert(pre_detail is not None, "pre_v1 render fetch failed")
        _assert(pre_detail["prompt"] is None,
                "F1 spec: pre_v1 render should have prompt=None per AD-3 forward-only")
        print(f"  PASS — pre_v1 render {pre_v1_id[0]} correctly has prompt=None (AD-3)")

    # --- F4 — Lineage anchoring (3 layers, queries answerable) ---
    print("\n=== F4 — Lineage anchoring ===")
    print("  Layer 1 — render→render: query incoming on R1 should return R2")
    t0 = time.perf_counter()
    r1_lineage = dispatcher.lineage_for_artifact("render", "test_acceptance_r1")
    elapsed = time.perf_counter() - t0
    _assert(elapsed < F1_BUDGET_SECONDS,
            f"F4 FAIL: layer 1 query took {elapsed:.3f}s, budget {F1_BUDGET_SECONDS}s")
    _assert(len(r1_lineage["incoming"]) == 1,
            f"F4 FAIL: R1 should have 1 incoming edge, got {len(r1_lineage['incoming'])}")
    _assert(r1_lineage["incoming"][0]["source_id"] == "test_acceptance_r2",
            f"F4 FAIL: incoming source mismatch: {r1_lineage['incoming'][0]}")
    _assert(r1_lineage["incoming"][0]["layer"] == 1, "layer should be 1 for render-render")
    _assert(len(r1_lineage["outgoing"]) == 0, "R1 has no outgoing edges in fixture")
    print(f"  PASS — R1 has 1 incoming edge (R2 cites R1) in {elapsed*1000:.1f}ms")

    print("\n  Layer 2 — concept→concept: query outgoing on C2 should return C1")
    t0 = time.perf_counter()
    c2_lineage = dispatcher.lineage_for_artifact("concept", "test_acceptance_c2")
    elapsed = time.perf_counter() - t0
    _assert(elapsed < F1_BUDGET_SECONDS, f"F4 FAIL: layer 2 query took {elapsed:.3f}s")
    _assert(len(c2_lineage["outgoing"]) == 1,
            f"F4 FAIL: C2 should anchor against 1 concept, got {len(c2_lineage['outgoing'])}")
    _assert(c2_lineage["outgoing"][0]["target_id"] == "test_acceptance_c1",
            f"F4 FAIL: outgoing target mismatch")
    _assert(c2_lineage["outgoing"][0]["layer"] == 2)
    print(f"  PASS — C2 anchors against C1 (layer 2) in {elapsed*1000:.1f}ms")

    print("\n  'What concepts informed this prompt?' via prompt → concept_id")
    detail = dispatcher.get_render_detail("test_acceptance_r1")
    concept_from_prompt = detail["concept"]
    _assert(concept_from_prompt["name"] == "h5_skinner_box",
            f"F4 FAIL: concept-from-prompt query failed: {concept_from_prompt}")
    print(f"  PASS — render r1 → prompt p1 → concept '{concept_from_prompt['name']}'")

    print("\n  Layer 3 — channel-arch→ep-arch→NOTES.md: schema supports it")
    print("  (no Phase 1 fixtures since NOTES.md authorship is Phase 3 territory;")
    print("   structural support verified by accepting layer=3 in create_lineage_edge)")
    edge3 = dispatcher.create_lineage_edge(
        source_type="notes_md", source_id="test_acceptance_notes_h5",
        target_type="ep_architecture", target_id="test_acceptance_ep1_arch_v1_4",
        layer=3,
    )
    _assert(edge3["layer"] == 3, "layer 3 edge should be creatable")
    print(f"  PASS — layer 3 edge created (notes_md → ep_architecture)")

    # --- F2 — Concept persistence (path verification, not timed walkthrough) ---
    print("\n=== F2 — Concept persistence (path verification) ===")
    print("  Spec criterion: <5min from 'open app' to 'ready to draft next prompt'")
    print("  This is a UX criterion; full walkthrough is in ACCEPTANCE.md.")
    print("  Path verification: required endpoints exist:")
    import app as _app
    routes = {r.path for r in _app.app.routes}
    for path_pattern in F2_PATH_REQUIRED_ENDPOINTS:
        _assert(path_pattern in routes,
                f"F2 FAIL: endpoint missing: {path_pattern}")
        print(f"    OK: {path_pattern}")
    print("  PASS — all F2 path endpoints present")

    # --- Cleanup ---
    print("\nCleanup...")
    cleanup()
    # Verify cleanup
    conn = db.connect()
    try:
        leaked = conn.execute(
            "SELECT COUNT(*) FROM concepts WHERE id LIKE 'test_acceptance_%'"
        ).fetchone()[0]
    finally:
        conn.close()
    _assert(leaked == 0, f"cleanup leaked {leaked} concepts")
    print("  ok")

    print("\n" + "="*60)
    print("PHASE 1 ACCEPTANCE: PASS")
    print("="*60)
    print("  F1 — render→prompt recoverable in <2s")
    print("  F2 — concept persistence path complete (UI walkthrough: ACCEPTANCE.md)")
    print("  F4 — lineage layer 1, 2, 3 queries answerable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
