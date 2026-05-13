#!/usr/bin/env python3
"""Phase 2 Wave A — audit module tests.

Exercises audit.py business logic directly (no HTTP):
  - audit_sessions lifecycle: create / list / get / end (idempotent)
  - get_render_detail: render + concept + verdict + lineage joins
  - capture_verdict: instant write + validation + supersession
  - update_verdict_flags: needs_second_look toggle
  - list_audit_queue: composable filters
  - get_session_cost: Wave A $0 baseline

Test data uses 'test_pwa_' prefix (phase 2 wave A) for cleanup via
db.cascading_delete (passes the test_-prefix guard).

Run: python tool_build/tests/test_audit.py
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (Pattern #3: import db for codec setup)
import audit  # noqa: E402
import dispatcher  # noqa: E402


PREFIX = "test_pwa_"


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def _seed_render(render_id: str, prompt_id: str = None) -> None:
    """Insert a synthetic render row for tests."""
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO renders (
                    id, attempt_id, prompt_id, filename, filepath,
                    download_hash, canonical_hash, tool, variant, hero_status,
                    discipline_version, yaml_path, created
                ) VALUES (?, NULL, ?, ?, ?, NULL, ?, ?, NULL, NULL, '1.0', NULL, '2026-05-06T00:00:00+00:00')
                """,
                (render_id, prompt_id,
                 f"{render_id}.png", f"test/path/{render_id}.png",
                 f"hash_{render_id}", "midjourney"),
            )
    finally:
        conn.close()


def _seed_concept_and_prompt(concept_id: str, prompt_id: str) -> None:
    """Synthetic concept + prompt for render-detail join testing."""
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO concepts (
                    id, name, ep, section, status, discipline_version,
                    yaml_path, created, modified
                ) VALUES (?, ?, 'ep1', 'h5_test', 'drafting', '1.0', ?, ?, ?)
                """,
                (concept_id, f"{concept_id}_name",
                 f"_data/concepts/{concept_id}.yaml",
                 "2026-05-06T00:00:00+00:00", "2026-05-06T00:00:00+00:00"),
            )
            conn.execute(
                """
                INSERT INTO prompts (
                    id, concept_id, tool, status, discipline_version,
                    yaml_path, created
                ) VALUES (?, ?, 'midjourney', 'draft', '1.0', ?, ?)
                """,
                (prompt_id, concept_id, f"_data/prompts/{prompt_id}.yaml",
                 "2026-05-06T00:00:00+00:00"),
            )
    finally:
        conn.close()


def cleanup():
    """Clean test rows + test YAMLs.

    The audit module derives verdict and audit_session IDs via sha256
    (no test_pwa_ prefix), so cascading_delete by id-prefix doesn't
    catch them. Clean by FK correlation:
      - ai_consultations via verdict.render_id LIKE test_pwa_%
      - verdicts via render_id LIKE test_pwa_%
      - audit_thumbnails via render_id LIKE test_pwa_%
    Then cascading_delete handles renders, prompts, concepts on id prefix.
    audit_sessions are cleaned per-test (each test that creates one
    deletes it explicitly at end-of-test).
    """
    conn = db.connect()
    try:
        with conn:
            # Track YAML paths to remove BEFORE deleting db rows.
            verdict_yamls = [r[0] for r in conn.execute(
                "SELECT yaml_path FROM verdicts WHERE render_id LIKE ?",
                (f"{PREFIX}%",)
            ).fetchall()]
            conn.execute(
                "DELETE FROM ai_consultations WHERE verdict_id IN ("
                "SELECT id FROM verdicts WHERE render_id LIKE ?)",
                (f"{PREFIX}%",),
            )
            conn.execute(
                "DELETE FROM verdicts WHERE render_id LIKE ?",
                (f"{PREFIX}%",),
            )
            conn.execute(
                "DELETE FROM audit_thumbnails WHERE render_id LIKE ?",
                (f"{PREFIX}%",),
            )
    finally:
        conn.close()
    # Now safe to cascading_delete renders / prompts / concepts.
    db.cascading_delete(PREFIX)
    # Clean tracked verdict YAMLs.
    repo_root = db.TOOL_BUILD_DIR.parent.parent.parent
    for yaml_rel in verdict_yamls:
        try:
            (repo_root / yaml_rel).unlink(missing_ok=True)
        except OSError:
            pass


def test_create_audit_session():
    """create_audit_session returns record with id, started, defaults; YAML written; row in db."""
    record = audit.create_audit_session(rubric_version="1.0", mode="quick_pass")
    session_id = record["id"]
    _assert(record["mode"] == "quick_pass")
    _assert(record["ended"] is None)
    _assert(record["total_consultations"] == 0)
    _assert(record["total_cost_usd"] == 0.0)

    # YAML present
    yaml_path = db.DATA_DIR / "audit_sessions" / f"{session_id}.yaml"
    _assert(yaml_path.exists(), f"YAML missing at {yaml_path}")

    # State.db row present
    fetched = audit.get_audit_session(session_id)
    _assert(fetched is not None and fetched["id"] == session_id)

    # Direct cleanup — session_id is sha256-derived, not test_pwa_-prefixed,
    # so the global cleanup() can't catch it.
    conn = db.connect()
    try:
        with conn:
            conn.execute("DELETE FROM audit_sessions WHERE id = ?", (session_id,))
    finally:
        conn.close()
    yaml_path.unlink(missing_ok=True)


def test_create_audit_session_invalid_mode():
    try:
        audit.create_audit_session(mode="invalid_mode")
    except ValueError as e:
        _assert("invalid mode" in str(e))
        return
    _assert(False, "expected ValueError on invalid mode")


def test_end_audit_session_idempotent():
    record = audit.create_audit_session(mode="quick_pass")
    sid = record["id"]
    ended_first = audit.end_audit_session(sid)
    _assert(ended_first["ended"] is not None)
    first_ended_ts = ended_first["ended"]

    # Re-end: should preserve original timestamp
    ended_second = audit.end_audit_session(sid)
    _assert(ended_second["ended"] == first_ended_ts,
            "second end_audit_session should preserve original ended timestamp")

    # Cleanup
    conn = db.connect()
    try:
        with conn:
            conn.execute("DELETE FROM audit_sessions WHERE id = ?", (sid,))
    finally:
        conn.close()
    (db.DATA_DIR / "audit_sessions" / f"{sid}.yaml").unlink(missing_ok=True)


def test_get_render_detail_with_joins():
    render_id = f"{PREFIX}render_join"
    concept_id = f"{PREFIX}concept_join"
    prompt_id = f"{PREFIX}prompt_join"
    _seed_concept_and_prompt(concept_id, prompt_id)
    _seed_render(render_id, prompt_id=prompt_id)

    detail = audit.get_render_detail(render_id)
    _assert(detail is not None)
    _assert(detail["id"] == render_id)
    _assert(detail["concept"] is not None)
    _assert(detail["concept"]["id"] == concept_id)
    _assert(detail["concept"]["section"] == "h5_test")
    _assert(detail["verdict"] is None, "no verdict yet -> None")
    _assert(detail["lineage_edges"] == [])


def test_get_render_detail_missing():
    _assert(audit.get_render_detail("nonexistent_render_id") is None)


def test_get_render_detail_includes_ai_consultations():
    """Phase 2.5 extension: detail response includes ai_consultations
    array for the latest verdict — empty list when no verdict, empty
    list when verdict but no consultations, populated when verdicts
    have ai_consultations rows."""
    render_id = f"{PREFIX}render_consultations"
    _seed_render(render_id)

    # No verdict -> ai_consultations is empty
    detail = audit.get_render_detail(render_id)
    _assert(detail["ai_consultations"] == [],
            "no verdict should yield empty ai_consultations array")

    # Verdict but no consultations -> still empty
    v = audit.capture_verdict(render_id=render_id, verdict="strong")
    detail = audit.get_render_detail(render_id)
    _assert(detail["ai_consultations"] == [])

    # Insert a synthetic ai_consultations row -> appears in detail
    import json as _json
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO ai_consultations (
                    id, verdict_id, provider, model, consulted_at,
                    status, cost_usd, used_downscale, raw_response,
                    parsed_json, failure_reason, yaml_path
                ) VALUES (?, ?, 'anthropic', 'claude-opus-4-7',
                          '2026-05-07T10:00:00+00:00', 'completed', 0.15,
                          1, 'fake raw',
                          ?, NULL, NULL)
                """,
                (
                    "test_consult_ai_row", v["id"],
                    _json.dumps({"verdict_inference": "strong",
                                 "criteria_match": {"Composition": "pass"}}),
                ),
            )
    finally:
        conn.close()

    detail = audit.get_render_detail(render_id)
    _assert(len(detail["ai_consultations"]) == 1)
    c = detail["ai_consultations"][0]
    _assert(c["provider"] == "anthropic")
    _assert(c["status"] == "completed")
    _assert(c["used_downscale"] is True)
    _assert(c["parsed"]["verdict_inference"] == "strong")

    # Cleanup the synthetic ai_consultation row (cascading_delete by
    # test_pwa_ prefix doesn't catch it since id was set explicitly).
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                "DELETE FROM ai_consultations WHERE id = ?",
                ("test_consult_ai_row",),
            )
    finally:
        conn.close()


def test_capture_verdict_basic():
    render_id = f"{PREFIX}render_basic"
    _seed_render(render_id)
    record = audit.capture_verdict(
        render_id=render_id, verdict="strong",
        verdict_reasoning="solid composition",
    )
    _assert(record["verdict"] == "strong")
    _assert(record["render_id"] == render_id)
    _assert(record["flags"]["needs_second_look"] is False)

    # YAML present
    yaml_path = db.DATA_DIR / "verdicts" / f"{record['id']}.yaml"
    _assert(yaml_path.exists())


def test_capture_verdict_invalid_type():
    render_id = f"{PREFIX}render_invalid_v"
    _seed_render(render_id)
    try:
        audit.capture_verdict(render_id=render_id, verdict="brilliant")
    except ValueError as e:
        _assert("invalid verdict" in str(e))
        return
    _assert(False, "expected ValueError on invalid verdict")


def test_capture_verdict_render_not_found():
    try:
        audit.capture_verdict(render_id="ghost_render", verdict="strong")
    except ValueError as e:
        _assert("not found" in str(e))
        return
    _assert(False, "expected ValueError on missing render")


def test_capture_verdict_with_flags():
    render_id = f"{PREFIX}render_flagged"
    _seed_render(render_id)
    record = audit.capture_verdict(
        render_id=render_id, verdict="weak",
        flags_needs_second_look=True,
    )
    _assert(record["flags"]["needs_second_look"] is True)

    # Detail surface should reflect flag
    detail = audit.get_render_detail(render_id)
    _assert(detail["verdict"]["flags_needs_second_look"] is True)


def test_update_verdict_flags():
    render_id = f"{PREFIX}render_flag_toggle"
    _seed_render(render_id)
    v = audit.capture_verdict(render_id=render_id, verdict="strong")
    updated = audit.update_verdict_flags(v["id"], needs_second_look=True)
    _assert(updated["flags_needs_second_look"] is True)

    # Toggle back
    updated2 = audit.update_verdict_flags(v["id"], needs_second_look=False)
    _assert(updated2["flags_needs_second_look"] is False)


def test_verdict_supersession():
    render_id = f"{PREFIX}render_super"
    _seed_render(render_id)
    v1 = audit.capture_verdict(render_id=render_id, verdict="weak",
                                verdict_reasoning="initial assessment")
    v2 = audit.capture_verdict(
        render_id=render_id, verdict="strong",
        verdict_reasoning="revised after rubric 1.1 bump",
        supersedes_verdict_id=v1["id"],
    )

    # get_render_detail returns the non-superseded one (v2)
    detail = audit.get_render_detail(render_id)
    _assert(detail["verdict"]["id"] == v2["id"],
            f"expected non-superseded {v2['id']}, got {detail['verdict']['id']}")
    _assert(detail["verdict"]["verdict"] == "strong")


def test_audit_queue_filters():
    # Seed 3 renders with distinct tools
    r1 = f"{PREFIX}q_r1"; r2 = f"{PREFIX}q_r2"; r3 = f"{PREFIX}q_r3"
    _seed_render(r1)
    _seed_render(r2)
    _seed_render(r3)
    # Mark r1 with verdict (so only_unverdicted excludes it)
    audit.capture_verdict(render_id=r1, verdict="hero_zone")
    # Mark r2 flagged (so flagged_only includes only r2)
    v2 = audit.capture_verdict(render_id=r2, verdict="weak",
                                flags_needs_second_look=True)

    # only_unverdicted: should NOT include r1 (r2, r3 yes)
    res = audit.list_audit_queue(only_unverdicted=True, limit=200)
    ids = [item["render_id"] for item in res["items"]]
    _assert(r1 not in ids)
    _assert(r3 in ids)

    # flagged_only: should include r2 only (among test renders)
    res = audit.list_audit_queue(flagged_only=True, limit=200)
    ids = [item["render_id"] for item in res["items"]]
    _assert(r2 in ids)
    _assert(r1 not in ids)
    _assert(r3 not in ids)


def test_session_cost_baseline():
    record = audit.create_audit_session(mode="deep_eval")
    sid = record["id"]
    cost = audit.get_session_cost(sid)
    _assert(cost is not None)
    _assert(cost["total_cost_usd"] == 0.0)
    _assert(cost["verdict_count"] == 0)
    _assert(cost["total_consultations"] == 0)

    # Cleanup
    conn = db.connect()
    try:
        with conn:
            conn.execute("DELETE FROM audit_sessions WHERE id = ?", (sid,))
    finally:
        conn.close()
    (db.DATA_DIR / "audit_sessions" / f"{sid}.yaml").unlink(missing_ok=True)


def main():
    cleanup()  # Pre-clean any prior failed-run state
    try:
        test_create_audit_session()
        test_create_audit_session_invalid_mode()
        test_end_audit_session_idempotent()
        test_get_render_detail_with_joins()
        test_get_render_detail_missing()
        test_get_render_detail_includes_ai_consultations()
        test_capture_verdict_basic()
        test_capture_verdict_invalid_type()
        test_capture_verdict_render_not_found()
        test_capture_verdict_with_flags()
        test_update_verdict_flags()
        test_verdict_supersession()
        test_audit_queue_filters()
        test_session_cost_baseline()
    finally:
        cleanup()
    print("PASS: audit module — sessions, render_detail, verdicts, "
          "supersession, queue, cost (Wave A non-AI scope)")
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_audit.py` invocation
    remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
