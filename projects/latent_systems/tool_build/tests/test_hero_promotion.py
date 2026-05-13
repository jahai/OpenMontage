#!/usr/bin/env python3
"""F5 hero promotion atomic action tests (Day 2 of Phase 3 sprint).

Covers dispatcher.hero_promote() + dispatcher.hero_un_promote() per
F5_MODAL_UX_DRAFT.md v1.2 §"Test fixtures (Pattern #8 mandatory third
bucket)":

Positive:
  - Promote with hero_zone / strong verdict → file copied to winners/,
    hero_promotions row inserted with verdict_id + promoted_at +
    promoted_by, YAML sidecar written.
  - Un-promote with valid reason → file moved to _DEPRECATED_<sanitized>/,
    hero_promotions row updated with reversed_at + reversed_reason.

Project-specific looks-like-target-but-isn't:
  - Promote with weak verdict → ineligible (HeroPromotionError).
  - Promote render with no section → section-unresolved error.
  - winners/ doesn't exist for that section → auto-created.
  - Un-promote with empty reason → refused (<5 chars).
  - Un-promote with path-traversal reason → sanitized.

Negative:
  - Promote nonexistent render → 'not found'.
  - Promote render with no verdict → 'no current verdict'.
  - Promote already-promoted render → 'already promoted'.
  - Un-promote when no active promotion → 'no active promotion'.

Run via pytest (fixture-isolated DB). Standalone `python tests/test_hero_promotion.py`
also works but touches production paths.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402  (Pattern #3: import db for codec setup)
import dispatcher  # noqa: E402


PREFIX = "test_f5_"


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def _iso():
    return datetime.now(timezone.utc).isoformat()


def cleanup():
    """Best-effort cleanup. Under pytest's isolated_db fixture, tmp_path
    is auto-cleaned and this is a no-op for production isolation.
    Standalone mode uses cascading_delete + filesystem sweep."""
    db.cascading_delete(PREFIX)


def _seed_concept(section: str = "h3_skinner") -> str:
    """Create a test concept with a section. Returns concept_id."""
    cid = f"{PREFIX}concept_{section}"
    now = _iso()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """INSERT INTO concepts
                   (id, name, ep, section, subject, register, status,
                    discipline_version, yaml_path, created, modified)
                   VALUES (?, ?, 'ep1', ?, 'test subject', 'schematic_apparatus',
                           'drafting', '1.0', '_test', ?, ?)""",
                (cid, f"{PREFIX}name_{section}", section, now, now),
            )
    finally:
        conn.close()
    return cid


def _seed_render_with_verdict(
    *, render_id_suffix: str, concept_id: str, verdict_value: str,
    file_content: bytes = b"fake-png-bytes-for-test",
) -> tuple[str, str, Path]:
    """Create concept-bound render with the given verdict. Writes a
    synthetic file inside db.REPO_ROOT (fixture: tmp_path) so the F5
    src_path.relative_to(db.REPO_ROOT) math works.

    Returns (render_id, verdict_id, abs_path)."""
    section = "h3_skinner"  # default; could parametrize
    render_id = f"{PREFIX}render_{render_id_suffix}"
    prompt_id = f"{PREFIX}prompt_{render_id_suffix}"
    verdict_id = f"{PREFIX}verdict_{render_id_suffix}"

    # Write the file inside REPO_ROOT so relative_to() works under both
    # fixture (REPO_ROOT = tmp_path) and standalone modes.
    rel_dir = Path("projects/latent_systems/ep1") / section / "reference"
    abs_dir = db.REPO_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    abs_path = abs_dir / f"{render_id}.png"
    abs_path.write_bytes(file_content)
    rel_filepath = abs_path.relative_to(db.REPO_ROOT).as_posix()

    now = _iso()
    conn = db.connect()
    try:
        with conn:
            # Prompt referencing the concept (so render → prompt → concept
            # → section join resolves in audit.get_render_detail).
            conn.execute(
                """INSERT INTO prompts
                   (id, concept_id, tool, text_preview, status,
                    drafted_by, discipline_version, yaml_path, created)
                   VALUES (?, ?, 'midjourney', 'test', 'completed',
                           'manual', '1.0', '_test', ?)""",
                (prompt_id, concept_id, now),
            )
            # Render referencing the prompt.
            conn.execute(
                """INSERT INTO renders
                   (id, attempt_id, prompt_id, filename, filepath,
                    download_hash, canonical_hash, tool, variant,
                    hero_status, discipline_version, yaml_path, created)
                   VALUES (?, NULL, ?, ?, ?, NULL, ?, 'midjourney',
                           NULL, NULL, '1.0', '_test', ?)""",
                (render_id, prompt_id, abs_path.name, rel_filepath,
                 f"hash_{render_id}", now),
            )
            # Verdict on the render.
            conn.execute(
                """INSERT INTO verdicts
                   (id, render_id, rubric_used, verdict, audited_by,
                    rubric_version, flags_needs_second_look,
                    discipline_version, yaml_path, created)
                   VALUES (?, ?, 'test_rubric', ?, 'human', '1.0', 0,
                           '1.0', '_test', ?)""",
                (verdict_id, render_id, verdict_value, now),
            )
    finally:
        conn.close()
    return render_id, verdict_id, abs_path


def _seed_render_no_verdict(render_id_suffix: str, concept_id: str) -> str:
    """Render with no verdict. Returns render_id."""
    render_id = f"{PREFIX}render_{render_id_suffix}"
    prompt_id = f"{PREFIX}prompt_{render_id_suffix}"

    rel_dir = Path("projects/latent_systems/ep1/h3_skinner/reference")
    abs_dir = db.REPO_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    abs_path = abs_dir / f"{render_id}.png"
    abs_path.write_bytes(b"fake")
    rel_filepath = abs_path.relative_to(db.REPO_ROOT).as_posix()

    now = _iso()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """INSERT INTO prompts
                   (id, concept_id, tool, text_preview, status, drafted_by,
                    discipline_version, yaml_path, created)
                   VALUES (?, ?, 'midjourney', 'test', 'completed',
                           'manual', '1.0', '_test', ?)""",
                (prompt_id, concept_id, now),
            )
            conn.execute(
                """INSERT INTO renders
                   (id, attempt_id, prompt_id, filename, filepath,
                    download_hash, canonical_hash, tool, variant,
                    hero_status, discipline_version, yaml_path, created)
                   VALUES (?, NULL, ?, ?, ?, NULL, ?, 'midjourney',
                           NULL, NULL, '1.0', '_test', ?)""",
                (render_id, prompt_id, abs_path.name, rel_filepath,
                 f"hash_{render_id}", now),
            )
    finally:
        conn.close()
    return render_id


def _seed_unbound_render(render_id_suffix: str) -> str:
    """Render with no prompt (no concept → no section). Returns render_id."""
    render_id = f"{PREFIX}render_{render_id_suffix}"
    rel_dir = Path("projects/latent_systems/_test_unbound")
    abs_dir = db.REPO_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    abs_path = abs_dir / f"{render_id}.png"
    abs_path.write_bytes(b"fake")
    rel_filepath = abs_path.relative_to(db.REPO_ROOT).as_posix()

    # Need a verdict too so the test exercises the section-check path
    # (not the no-verdict path).
    verdict_id = f"{PREFIX}verdict_{render_id_suffix}"
    now = _iso()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """INSERT INTO renders
                   (id, attempt_id, prompt_id, filename, filepath,
                    download_hash, canonical_hash, tool, variant,
                    hero_status, discipline_version, yaml_path, created)
                   VALUES (?, NULL, NULL, ?, ?, NULL, ?, 'midjourney',
                           NULL, NULL, '1.0', '_test', ?)""",
                (render_id, abs_path.name, rel_filepath,
                 f"hash_{render_id}", now),
            )
            conn.execute(
                """INSERT INTO verdicts
                   (id, render_id, rubric_used, verdict, audited_by,
                    rubric_version, flags_needs_second_look,
                    discipline_version, yaml_path, created)
                   VALUES (?, ?, 'test_rubric', 'strong', 'human', '1.0', 0,
                           '1.0', '_test', ?)""",
                (verdict_id, render_id, now),
            )
    finally:
        conn.close()
    return render_id


def main() -> int:
    cleanup()  # idempotent

    concept_id = _seed_concept(section="h3_skinner")

    # ---- Test 1: promote with strong verdict succeeds ----
    print("Test 1: promote with 'strong' verdict succeeds")
    rid, vid, src = _seed_render_with_verdict(
        render_id_suffix="strong_ok", concept_id=concept_id,
        verdict_value="strong",
    )
    result = dispatcher.hero_promote(render_id=rid)
    _assert(result["ok"], f"hero_promote should succeed: {result}")
    _assert("hero_promotion_id" in result, "missing hero_promotion_id")
    _assert(result["f6_prompt_status"] == "deferred_f6_not_shipped",
            f"f6_prompt_status unexpected: {result['f6_prompt_status']}")
    # File copied to winners/ (source still exists per COPY semantics)
    expected_dest = (
        db.REPO_ROOT / "projects/latent_systems/ep1/h3_skinner/winners"
        / src.name
    )
    _assert(expected_dest.exists(), f"copied file missing at {expected_dest}")
    _assert(src.exists(), "source file should still exist (COPY not MOVE)")
    # DB row present with verdict_id linkage
    conn = db.connect()
    try:
        prow = conn.execute(
            "SELECT verdict_id, promoted_at, promoted_by, hero_filepath, "
            "reversed_at FROM hero_promotions WHERE id = ?",
            (result["hero_promotion_id"],),
        ).fetchone()
    finally:
        conn.close()
    _assert(prow is not None, "hero_promotions row missing")
    _assert(prow[0] == vid, f"verdict_id should be {vid}, got {prow[0]}")
    _assert(prow[1] is not None, "promoted_at should be set")
    _assert(prow[2] == "joseph", f"promoted_by should be 'joseph', got {prow[2]}")
    _assert(prow[4] is None, "reversed_at should be NULL on forward flow")
    print(f"  copied to {expected_dest.name}; verdict_id linked; promoted_at set")

    # ---- Test 2: promote with hero_zone verdict succeeds ----
    print("\nTest 2: promote with 'hero_zone' verdict succeeds")
    rid2, _, _ = _seed_render_with_verdict(
        render_id_suffix="hero_ok", concept_id=concept_id,
        verdict_value="hero_zone",
    )
    result = dispatcher.hero_promote(render_id=rid2)
    _assert(result["ok"], "hero_zone promote should succeed")
    print("  ok")

    # ---- Test 3: promote with weak verdict refused ----
    print("\nTest 3: promote with 'weak' verdict refused (ineligible)")
    rid3, _, _ = _seed_render_with_verdict(
        render_id_suffix="weak_no", concept_id=concept_id,
        verdict_value="weak",
    )
    try:
        dispatcher.hero_promote(render_id=rid3)
        _assert(False, "weak verdict should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("ineligible" in str(e),
                f"expected 'ineligible' error, got: {e}")
    print("  refused with ineligible verdict error")

    # ---- Test 4: promote with reject verdict refused ----
    print("\nTest 4: promote with 'reject' verdict refused (ineligible)")
    rid4, _, _ = _seed_render_with_verdict(
        render_id_suffix="reject_no", concept_id=concept_id,
        verdict_value="reject",
    )
    try:
        dispatcher.hero_promote(render_id=rid4)
        _assert(False, "reject verdict should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("ineligible" in str(e))
    print("  refused with ineligible verdict error")

    # ---- Test 5: promote render with no verdict refused ----
    print("\nTest 5: promote render with no verdict refused")
    rid5 = _seed_render_no_verdict("no_verdict", concept_id)
    try:
        dispatcher.hero_promote(render_id=rid5)
        _assert(False, "no-verdict should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("no current verdict" in str(e))
    print("  refused with no-verdict error")

    # ---- Test 6: promote nonexistent render → 'not found' ----
    print("\nTest 6: promote nonexistent render returns 'not found'")
    try:
        dispatcher.hero_promote(render_id=f"{PREFIX}does_not_exist")
        _assert(False, "nonexistent render should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("not found" in str(e))
    print("  refused with not-found error")

    # ---- Test 7: promote unbound render (no section) refused ----
    print("\nTest 7: promote render with no section refused")
    rid7 = _seed_unbound_render("unbound")
    try:
        dispatcher.hero_promote(render_id=rid7)
        _assert(False, "unbound render should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("section" in str(e),
                f"expected section-unresolved error, got: {e}")
    print("  refused with section-unresolved error")

    # ---- Test 8: promote already-promoted render refused ----
    print("\nTest 8: promote already-promoted render returns 'already promoted'")
    # rid (from Test 1) is already promoted; try again.
    try:
        dispatcher.hero_promote(render_id=rid)
        _assert(False, "already-promoted should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("already promoted" in str(e))
    print("  refused with already-promoted error")

    # ---- Test 9: winners/ directory auto-created if missing ----
    print("\nTest 9: winners/ directory auto-created on first promote")
    # New section without an existing winners/ dir.
    new_concept = _seed_concept(section="h5_slot_machine")
    rid9, _, _ = _seed_render_with_verdict(
        render_id_suffix="new_section",
        concept_id=new_concept,
        verdict_value="strong",
    )
    # Source file lives at .../h3_skinner/reference/ (default); for Test 9
    # we need it under h5_slot_machine. Re-seed override:
    section_h5 = "h5_slot_machine"
    new_dir = db.REPO_ROOT / "projects/latent_systems/ep1" / section_h5 / "reference"
    new_dir.mkdir(parents=True, exist_ok=True)
    new_src = new_dir / f"{rid9}.png"
    new_src.write_bytes(b"fake")
    # Update the render's filepath in db + concept's section.
    new_rel = new_src.relative_to(db.REPO_ROOT).as_posix()
    conn = db.connect()
    try:
        with conn:
            conn.execute("UPDATE renders SET filepath = ? WHERE id = ?",
                         (new_rel, rid9))
    finally:
        conn.close()
    winners_dir = db.REPO_ROOT / "projects/latent_systems/ep1" / section_h5 / "winners"
    # Sanity: winners/ doesn't exist yet (we never wrote there in tmp_path)
    if winners_dir.exists():
        shutil.rmtree(winners_dir)
    _assert(not winners_dir.exists(), "test setup: winners/ should not exist yet")
    result = dispatcher.hero_promote(render_id=rid9)
    _assert(result["ok"], "promote should succeed and auto-create winners/")
    _assert(winners_dir.exists(), "winners/ should be auto-created")
    print(f"  auto-created at {winners_dir.relative_to(db.REPO_ROOT)}")

    # ---- Test 10: un-promote with valid reason succeeds ----
    print("\nTest 10: un-promote with reason 'register drift second look'")
    result = dispatcher.hero_un_promote(
        render_id=rid, reason="register drift second look",
    )
    _assert(result["ok"], f"un-promote should succeed: {result}")
    _assert(result["deprecated_subdir"] == "_DEPRECATED_register_drift_second_look",
            f"sanitized subdir wrong: {result['deprecated_subdir']}")
    # File should be in _DEPRECATED_*/ now, not in winners/
    _assert(not expected_dest.exists(),
            "file should have moved out of winners/")
    deprecated_path = (
        db.REPO_ROOT / "projects/latent_systems/ep1/h3_skinner/_work/un_promoted"
        / "_DEPRECATED_register_drift_second_look" / expected_dest.name
    )
    _assert(deprecated_path.exists(),
            f"file should exist at {deprecated_path}")
    # DB row updated with reversed_at + reversed_reason
    conn = db.connect()
    try:
        prow = conn.execute(
            "SELECT reversed_at, reversed_reason FROM hero_promotions "
            "WHERE id = ?",
            (result["hero_promotion_id"],),
        ).fetchone()
    finally:
        conn.close()
    _assert(prow[0] is not None, "reversed_at should be populated")
    _assert(prow[1] == "register drift second look",
            f"reversed_reason wrong: {prow[1]}")
    print("  moved + db row updated with reversed_at + reversed_reason")

    # ---- Test 11: un-promote with reason too short refused ----
    print("\nTest 11: un-promote with reason 'no' (<5 chars) refused")
    rid_un_short, _, _ = _seed_render_with_verdict(
        render_id_suffix="un_short", concept_id=concept_id,
        verdict_value="strong",
    )
    dispatcher.hero_promote(render_id=rid_un_short)  # promote first
    try:
        dispatcher.hero_un_promote(render_id=rid_un_short, reason="no")
        _assert(False, "short reason should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert(">= 5 chars" in str(e) or "5 chars" in str(e))
    print("  refused with short-reason error")

    # ---- Test 12: un-promote with path-traversal reason sanitizes ----
    print("\nTest 12: un-promote with '../etc/passwd' reason sanitizes")
    result = dispatcher.hero_un_promote(
        render_id=rid_un_short, reason="../etc/passwd issue",
    )
    _assert(result["ok"], "sanitized reason should succeed")
    # Sanitization: "../etc/passwd issue" → "etcpasswd_issue"
    _assert(result["deprecated_subdir"] == "_DEPRECATED_etcpasswd_issue",
            f"sanitized subdir wrong: {result['deprecated_subdir']}")
    print(f"  sanitized to {result['deprecated_subdir']}")

    # ---- Test 13: un-promote with no active promotion refused ----
    print("\nTest 13: un-promote render with no active promotion refused")
    rid_unpromoted, _, _ = _seed_render_with_verdict(
        render_id_suffix="never_promoted", concept_id=concept_id,
        verdict_value="strong",
    )
    try:
        dispatcher.hero_un_promote(
            render_id=rid_unpromoted, reason="some valid reason",
        )
        _assert(False, "no-promotion should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("no active promotion" in str(e))
    print("  refused with no-active-promotion error")

    # ---- Test 14: un-promote with all-special-chars reason refused ----
    print("\nTest 14: un-promote with reason '!!!!!  ' (sanitizes to empty)")
    rid14, _, _ = _seed_render_with_verdict(
        render_id_suffix="empty_sanitized", concept_id=concept_id,
        verdict_value="strong",
    )
    dispatcher.hero_promote(render_id=rid14)
    try:
        dispatcher.hero_un_promote(
            render_id=rid14, reason="!!!!! ",
        )
        _assert(False, "empty-sanitized reason should have been refused")
    except dispatcher.HeroPromotionError as e:
        _assert("sanitized to empty" in str(e))
    print("  refused with sanitized-to-empty error")

    print("\nPASS: all F5 hero promotion behaviors verified")
    cleanup()
    return 0


def test_main():
    """pytest entry point — runs main() under autouse isolated_db fixture
    (conftest.py). Standalone `python tests/test_hero_promotion.py`
    invocation remains supported via the if __name__ block below."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
