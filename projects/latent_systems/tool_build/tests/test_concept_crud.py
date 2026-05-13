#!/usr/bin/env python3
"""Day 14 — Feature 1 concept CRUD.

Tests:
  1. create_concept basic + status defaults
  2. create_concept rejects empty name + invalid status
  3. get_concept returns full record + (empty) joined artifacts
  4. list_concepts filters by ep/section/status/register
  5. list_concepts excludes archived by default
  6. update_concept substantive edit bumps discipline_version
  7. update_concept status-only edit does NOT bump discipline_version
  8. update_concept rejects unknown fields + invalid status
  9. archive_concept sets status='archived' and excludes from default list
  10. get_concept joins linked prompts (when prompts.concept_id matches)

Test data uses 'test_d14_' prefix for cleanup.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
import dispatcher  # noqa: E402
from constants import CURRENT_DISCIPLINE_VERSION  # noqa: E402


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def cleanup():
    conn = db.connect()
    try:
        with conn:
            # FK-respecting order; concept ids start with sha256 hashes — we
            # tag test concepts via name prefix. Find by name then delete.
            test_ids = [r[0] for r in conn.execute(
                "SELECT id FROM concepts WHERE name LIKE 'test_d14_%'"
            ).fetchall()]
            for cid in test_ids:
                # Delete linked artifacts first
                conn.execute("DELETE FROM verdicts WHERE render_id IN ("
                             "SELECT id FROM renders WHERE prompt_id IN ("
                             "SELECT id FROM prompts WHERE concept_id = ?))", (cid,))
                conn.execute("DELETE FROM hero_promotions WHERE render_id IN ("
                             "SELECT id FROM renders WHERE prompt_id IN ("
                             "SELECT id FROM prompts WHERE concept_id = ?))", (cid,))
                conn.execute("DELETE FROM api_calls WHERE prompt_id IN ("
                             "SELECT id FROM prompts WHERE concept_id = ?)", (cid,))
                conn.execute("DELETE FROM renders WHERE prompt_id IN ("
                             "SELECT id FROM prompts WHERE concept_id = ?)", (cid,))
                conn.execute("DELETE FROM generation_attempts WHERE prompt_id IN ("
                             "SELECT id FROM prompts WHERE concept_id = ?)", (cid,))
                conn.execute("DELETE FROM prompts WHERE concept_id = ?", (cid,))
            conn.execute("DELETE FROM concepts WHERE name LIKE 'test_d14_%'")
    finally:
        conn.close()
    # Delete YAMLs
    for cid in []:
        pass
    for f in (db.DATA_DIR / "concepts").glob("*.yaml"):
        try:
            import yaml as _yaml
            data = _yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if str(data.get("name", "")).startswith("test_d14_"):
                f.unlink()
        except Exception:
            pass


def main() -> int:
    cleanup()

    # ---- Test 1: create_concept basic ----
    print("Test 1: create_concept basic + defaults")
    record = dispatcher.create_concept(
        name="test_d14_skinner_box",
        ep="ep1", section="h5_slot_machine",
        subject="rat at slot machine lever",
        register="schematic_apparatus",
    )
    _assert(record["id"], "concept id missing")
    _assert(record["name"] == "test_d14_skinner_box")
    _assert(record["status"] == "drafting", f"default status: {record['status']}")
    _assert(record["discipline_version"] == CURRENT_DISCIPLINE_VERSION)
    _assert(record["created"] == record["modified"])
    print(f"  created concept {record['id']}")

    # YAML written?
    yaml_abs = db.DATA_DIR / "concepts" / f"{record['id']}.yaml"
    _assert(yaml_abs.exists(), f"concept yaml missing at {yaml_abs}")

    # ---- Test 2: create_concept validates ----
    print("\nTest 2: create_concept rejects empty name + invalid status")
    try:
        dispatcher.create_concept(name="")
        _assert(False, "should have rejected empty name")
    except ValueError:
        pass
    try:
        dispatcher.create_concept(name="test_d14_bad_status", status="invented_state")
        _assert(False, "should have rejected invalid status")
    except ValueError:
        pass
    print("  validation works")

    # ---- Test 3: get_concept basic ----
    print("\nTest 3: get_concept returns full record + empty artifact lists")
    fetched = dispatcher.get_concept(record["id"])
    _assert(fetched is not None)
    _assert(fetched["name"] == "test_d14_skinner_box")
    _assert(fetched["prompts"] == [], "no prompts yet")
    _assert(fetched["renders"] == [])
    _assert(fetched["verdicts"] == [])
    _assert(fetched["hero_promotions"] == [])
    print("  joined artifact lists initialized empty")

    missing = dispatcher.get_concept("no_such_concept")
    _assert(missing is None, f"missing concept should return None, got {missing}")

    # ---- Test 4: list_concepts filters ----
    print("\nTest 4: list_concepts with filters")
    dispatcher.create_concept(name="test_d14_other", ep="ep2", status="drafting")
    dispatcher.create_concept(name="test_d14_locked", ep="ep1",
                              section="h5_slot_machine", status="locked")
    by_ep = [c for c in dispatcher.list_concepts(ep="ep1")
             if c["name"].startswith("test_d14_")]
    _assert(len(by_ep) >= 2, f"expected >=2 ep1 concepts, got {len(by_ep)}")
    by_status = [c for c in dispatcher.list_concepts(status="locked")
                 if c["name"].startswith("test_d14_")]
    _assert(len(by_status) == 1)
    by_section = [c for c in dispatcher.list_concepts(section="h5_slot_machine")
                  if c["name"].startswith("test_d14_")]
    _assert(len(by_section) >= 2)
    print("  ep, section, status filters work")

    # ---- Test 5: substantive edit bumps discipline_version ----
    print("\nTest 5: substantive edit bumps discipline_version")
    # Create at non-current version
    odd_record = dispatcher.create_concept(
        name="test_d14_old_version",
        discipline_version="0.9",
    )
    _assert(odd_record["discipline_version"] == "0.9")

    # Substantive edit: change subject -> bumps to current
    updated = dispatcher.update_concept(
        odd_record["id"],
        fields={"subject": "newly added subject"},
    )
    _assert(updated["discipline_version"] == CURRENT_DISCIPLINE_VERSION,
            f"substantive edit should bump: {updated['discipline_version']}")
    _assert(updated["modified"] != odd_record["modified"])
    print(f"  substantive edit: 0.9 -> {updated['discipline_version']}")

    # ---- Test 6: status-only edit does NOT bump ----
    print("\nTest 6: status-only edit preserves discipline_version")
    odd_b = dispatcher.create_concept(
        name="test_d14_status_only",
        discipline_version="0.9",
    )
    updated_b = dispatcher.update_concept(odd_b["id"], fields={"status": "evaluated"})
    _assert(updated_b["discipline_version"] == "0.9",
            f"status edit should NOT bump: {updated_b['discipline_version']}")
    _assert(updated_b["status"] == "evaluated")
    print(f"  status-only edit: discipline stayed at 0.9")

    # ---- Test 7: update_concept rejects unknown fields ----
    print("\nTest 7: update_concept rejects unknown fields + invalid status")
    try:
        dispatcher.update_concept(record["id"], fields={"random_field": "x"})
        _assert(False, "should have rejected unknown field")
    except ValueError:
        pass
    try:
        dispatcher.update_concept(record["id"], fields={"status": "made_up"})
        _assert(False, "should have rejected invalid status")
    except ValueError:
        pass
    print("  validation works")

    # ---- Test 8: update_concept on missing concept ----
    print("\nTest 8: update_concept on missing concept raises")
    try:
        dispatcher.update_concept("no_such_id", fields={"name": "x"})
        _assert(False, "should have raised")
    except ValueError:
        pass
    print("  missing concept rejected")

    # ---- Test 9: archive_concept ----
    print("\nTest 9: archive_concept sets status='archived' + excludes from default list")
    archive_record = dispatcher.create_concept(name="test_d14_to_archive")
    archived = dispatcher.archive_concept(archive_record["id"])
    _assert(archived["status"] == "archived")
    # Default list should NOT include
    default_list = [c for c in dispatcher.list_concepts()
                    if c["id"] == archive_record["id"]]
    _assert(len(default_list) == 0, "archived should be excluded from default list")
    # include_archived=True should include
    full_list = [c for c in dispatcher.list_concepts(include_archived=True)
                 if c["id"] == archive_record["id"]]
    _assert(len(full_list) == 1, "archived should appear with include_archived=True")
    print("  archive + visibility ok")

    # ---- Test 10: get_concept joins linked prompts ----
    print("\nTest 10: get_concept joins linked prompts")
    # Create a prompt linked to test_d14_skinner_box
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO prompts (id, concept_id, tool, text_preview, "
                "status, drafted_by, discipline_version, yaml_path, created) "
                "VALUES ('test_d14_p1', ?, 'midjourney', 'test prompt', "
                "'draft', 'manual', '1.0', '_t', ?)",
                (record["id"], dispatcher._iso_now()),
            )
    finally:
        conn.close()

    full = dispatcher.get_concept(record["id"])
    _assert(len(full["prompts"]) == 1)
    _assert(full["prompts"][0]["id"] == "test_d14_p1")
    _assert(full["prompts"][0]["tool"] == "midjourney")
    print(f"  concept detail returned linked prompt: {full['prompts'][0]['id']}")

    print("\nTest 11: cleanup")
    cleanup()
    remaining = [c for c in dispatcher.list_concepts(include_archived=True)
                 if c["name"].startswith("test_d14_")]
    _assert(len(remaining) == 0, f"leftover: {remaining}")
    print("  ok")

    print("\nPASS: all Day 14 concept-CRUD behaviors verified")
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_concept_crud.py` invocation
    remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
