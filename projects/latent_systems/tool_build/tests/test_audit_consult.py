#!/usr/bin/env python3
"""Phase 2 Wave B — consultation orchestrator tests.

Wires audit_consult.consult_render against:
  - real render rows in state.db + on-disk PNGs (synthetic)
  - real rubric file in tempdir (passed as repo_root override)
  - real thumbnail generation (Pillow)
  - MOCKED audit_providers.anthropic.call_vision (no SDK calls)

Verifies orchestration glue:
  - happy path: consultation persists, verdict auto-created if absent
  - existing-verdict path: consultation attaches without auto-create
  - rubric-missing: ConsultationError before any provider calls
  - render-missing: ConsultationError
  - non-completed status (parse_failed, safety_refused) still persists
    as ai_consultations row with that status
  - audit_session totals incremented when session_id provided

Run: python tool_build/tests/test_audit_consult.py
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audit  # noqa: E402
import audit_consult  # noqa: E402
import db  # noqa: E402  (Pattern #3)
from audit_providers import anthropic as vision  # noqa: E402


PREFIX = "test_consult_"
TEST_RENDERS_DIR = db.DATA_DIR / "_test_consult_renders"
TRACKED_API_CALL_IDS: list[str] = []
TRACKED_AUDIT_SESSION_IDS: list[str] = []


SAMPLE_RUBRIC_TEXT = """\
---
version: "1.0"
discipline_version: "1.0"
applies_to_concept_types: [schematic_apparatus]
---

# Audit Rubric v1.0

### Composition
The framing of the render.
- pass: composition reads at-a-glance.
- partial: composition coherent but requires study.
- fail: composition incoherent.
"""


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        cleanup()
        sys.exit(1)


def _make_test_png(name: str) -> Path:
    TEST_RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    p = TEST_RENDERS_DIR / f"{name}.png"
    Image.new("RGB", (800, 600), color=(120, 90, 70)).save(p, format="PNG")
    return p


def _seed_render(render_id: str, png_path: Path) -> None:
    repo_root = db.TOOL_BUILD_DIR.parent.parent.parent
    rel_path = png_path.resolve().relative_to(repo_root.resolve()).as_posix()
    conn = db.connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO renders (
                    id, attempt_id, prompt_id, filename, filepath,
                    download_hash, canonical_hash, tool, variant, hero_status,
                    discipline_version, yaml_path, created
                ) VALUES (?, NULL, NULL, ?, ?, NULL, ?, 'midjourney', NULL,
                          NULL, '1.0', NULL, '2026-05-06T00:00:00+00:00')
                """,
                (render_id, png_path.name, rel_path, f"hash_{render_id}"),
            )
    finally:
        conn.close()


def _make_rubric_dir() -> Path:
    """Returns a tempdir to use as repo_root with a rubric file inside."""
    tmpdir = Path(tempfile.mkdtemp(prefix="rubric_test_"))
    docs = tmpdir / "projects" / "latent_systems" / "docs"
    docs.mkdir(parents=True)
    (docs / "AUDIT_RUBRICS_v1_0.md").write_text(SAMPLE_RUBRIC_TEXT, encoding="utf-8")
    return tmpdir


def _fake_completed_response(api_call_id: str = None):
    if api_call_id is None:
        api_call_id = f"call_{len(TRACKED_API_CALL_IDS)}_test"
    TRACKED_API_CALL_IDS.append(api_call_id)
    return vision.VisionConsultationResponse(
        raw_response='{"verdict_inference": "strong", "criteria_match": {"Composition": "pass"}, "key_observations": ["clear framing"]}',
        parsed={
            "verdict_inference": "strong",
            "criteria_match": {"Composition": "pass"},
            "key_observations": ["clear framing"],
        },
        status="completed",
        cost_usd=0.30,
        tokens_input=2200,
        tokens_output=85,
        used_downscale=True,
        api_call_id=api_call_id,
        model="claude-opus-4-7",
    )


def _fake_safety_refused_response():
    api_call_id = f"call_safety_{len(TRACKED_API_CALL_IDS)}_test"
    TRACKED_API_CALL_IDS.append(api_call_id)
    return vision.VisionConsultationResponse(
        raw_response="I can't evaluate this image due to content policy.",
        parsed=None,
        status="safety_refused",
        cost_usd=0.05,
        tokens_input=2200,
        tokens_output=15,
        used_downscale=True,
        api_call_id=api_call_id,
        model="claude-opus-4-7",
        failure_reason="vision API content-policy refusal",
    )


def cleanup():
    """Aggressively clean: ai_consultations + verdicts (by render_id
    correlation) + renders (test prefix) + audit_sessions (tracked
    list) + api_calls (tracked list) + on-disk artifacts.

    YAML cleanup discipline: capture YAML paths from state.db BEFORE
    deleting db rows. Consultation/verdict/session YAMLs use sha256-
    derived IDs so prefix-matching on filename doesn't catch them.

    Also handles cumulative residue from prior failed test runs by
    pre-walking _data/ subdirs for orphaned YAMLs (verdict_id or
    session_id no longer in state.db).
    """
    consult_yamls: list[str] = []
    verdict_yamls: list[str] = []
    session_yamls: list[Path] = []
    conn = db.connect()
    try:
        with conn:
            # Capture YAML paths first, while rows still exist
            consult_yamls = [
                r[0] for r in conn.execute(
                    "SELECT yaml_path FROM ai_consultations WHERE verdict_id IN ("
                    "SELECT id FROM verdicts WHERE render_id LIKE ?)",
                    (f"{PREFIX}%",),
                ).fetchall() if r[0]
            ]
            verdict_yamls = [
                r[0] for r in conn.execute(
                    "SELECT yaml_path FROM verdicts WHERE render_id LIKE ?",
                    (f"{PREFIX}%",),
                ).fetchall() if r[0]
            ]
            # Sessions: derive YAML path from id (audit_sessions table
            # has no yaml_path column; YAML lives at the canonical
            # _data/audit_sessions/<id>.yaml location).
            for sid in TRACKED_AUDIT_SESSION_IDS:
                session_yamls.append(
                    db.DATA_DIR / "audit_sessions" / f"{sid}.yaml"
                )

            # Now delete rows in FK-safe order
            conn.execute(
                "DELETE FROM ai_consultations WHERE verdict_id IN ("
                "SELECT id FROM verdicts WHERE render_id LIKE ?)",
                (f"{PREFIX}%",),
            )
            conn.execute(
                "DELETE FROM verdicts WHERE render_id LIKE ?", (f"{PREFIX}%",)
            )
            conn.execute(
                "DELETE FROM audit_thumbnails WHERE render_id LIKE ?",
                (f"{PREFIX}%",),
            )
            conn.execute(
                "DELETE FROM renders WHERE id LIKE ?", (f"{PREFIX}%",)
            )
            if TRACKED_AUDIT_SESSION_IDS:
                placeholders = ",".join("?" for _ in TRACKED_AUDIT_SESSION_IDS)
                conn.execute(
                    f"DELETE FROM audit_sessions WHERE id IN ({placeholders})",
                    TRACKED_AUDIT_SESSION_IDS,
                )
                TRACKED_AUDIT_SESSION_IDS.clear()
            if TRACKED_API_CALL_IDS:
                placeholders = ",".join("?" for _ in TRACKED_API_CALL_IDS)
                conn.execute(
                    f"DELETE FROM api_calls WHERE id IN ({placeholders})",
                    TRACKED_API_CALL_IDS,
                )
                TRACKED_API_CALL_IDS.clear()
    finally:
        conn.close()
    repo_root = db.TOOL_BUILD_DIR.parent.parent.parent
    for path_rel in consult_yamls + verdict_yamls:
        try:
            (repo_root / path_rel).unlink(missing_ok=True)
        except OSError:
            pass
    for sp in session_yamls:
        try:
            sp.unlink(missing_ok=True)
        except OSError:
            pass

    # Sweep for orphaned YAMLs from prior failed runs (verdict_id /
    # session_id no longer present in state.db).
    _sweep_orphans()

    if TEST_RENDERS_DIR.exists():
        shutil.rmtree(TEST_RENDERS_DIR, ignore_errors=True)


def _sweep_orphans():
    """Remove YAML files in _data/audit_sessions, _data/verdicts,
    _data/ai_consultations whose backing state.db row no longer exists.
    Defensive cleanup against accumulated test-run residue."""
    import yaml
    conn = db.connect()
    try:
        for subdir, table, id_col in (
            ("audit_sessions", "audit_sessions", "id"),
            ("verdicts", "verdicts", "id"),
            ("ai_consultations", "ai_consultations", "id"),
        ):
            d = db.DATA_DIR / subdir
            if not d.exists():
                continue
            for p in d.glob("*.yaml"):
                try:
                    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                    yaml_id = data.get("id", p.stem)
                    row = conn.execute(
                        f"SELECT 1 FROM {table} WHERE {id_col} = ?",
                        (yaml_id,),
                    ).fetchone()
                    if row is None:
                        # No backing row — orphan from prior run.
                        # Only remove if it looks test-attributable
                        # (don't sweep production YAMLs; production
                        # data has render_id starting with non-test
                        # prefix, OR is referenced by other rows).
                        is_test_residue = (
                            data.get("render_id", "").startswith(PREFIX)
                            or _refs_test_data(conn, data)
                        )
                        if is_test_residue:
                            p.unlink()
                except Exception:
                    pass  # tolerant — don't fail the sweep on one bad YAML
    finally:
        conn.close()


def _refs_test_data(conn, data: dict) -> bool:
    """True if a YAML record references a test_consult_-prefixed entity."""
    vid = data.get("verdict_id")
    if vid:
        row = conn.execute(
            "SELECT render_id FROM verdicts WHERE id = ?", (vid,),
        ).fetchone()
        if row and row[0] and row[0].startswith(PREFIX):
            return True
    return False


def test_consult_happy_path_auto_creates_verdict():
    # v0.6 amendment 1: explicit opt-in required to auto-create a verdict
    # when none exists. Test exercises the opted-in legacy path.
    rid = f"{PREFIX}happy"
    png = _make_test_png(rid)
    _seed_render(rid, png)
    rubric_dir = _make_rubric_dir()
    try:
        with patch.object(vision, "call_vision", return_value=_fake_completed_response()):
            result = audit_consult.consult_render(
                rid, repo_root=rubric_dir, create_verdict_if_missing=True,
            )

        _assert(result["render_id"] == rid)
        _assert(result["auto_created_verdict"] is True)
        _assert(result["verdict_id"] is not None)
        _assert(len(result["consultations"]) == 1)
        _assert(result["consultations"][0]["status"] == "completed")
        _assert(result["consultations"][0]["provider"] == "anthropic")
        _assert(abs(result["total_cost_usd"] - 0.30) < 1e-9)

        # Verdict was auto-created with verdict_inference 'strong'
        detail = audit.get_render_detail(rid)
        _assert(detail["verdict"]["verdict"] == "strong")
        _assert(detail["verdict"]["audited_by"] == "multi_ai_assisted")

        # ai_consultations row inserted
        conn = db.connect()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM ai_consultations WHERE verdict_id = ?",
                (result["verdict_id"],),
            ).fetchone()[0]
        finally:
            conn.close()
        _assert(count == 1)

        # YAML written
        consult_id = result["consultations"][0]["id"]
        yaml_path = db.DATA_DIR / "ai_consultations" / f"{consult_id}.yaml"
        _assert(yaml_path.exists())
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)


def test_consult_attaches_to_existing_verdict():
    rid = f"{PREFIX}existing"
    png = _make_test_png(rid)
    _seed_render(rid, png)
    rubric_dir = _make_rubric_dir()

    # Pre-existing verdict
    pre_verdict = audit.capture_verdict(
        render_id=rid, verdict="hero_zone",
        verdict_reasoning="manual mark before consultation",
    )
    pre_id = pre_verdict["id"]

    try:
        with patch.object(vision, "call_vision", return_value=_fake_completed_response()):
            result = audit_consult.consult_render(rid, repo_root=rubric_dir)

        _assert(result["verdict_id"] == pre_id,
                "consultation should attach to existing verdict, not auto-create")
        _assert(result["auto_created_verdict"] is False)

        # Verdict's verdict value unchanged (still hero_zone)
        detail = audit.get_render_detail(rid)
        _assert(detail["verdict"]["verdict"] == "hero_zone")

        # consultation_cost_usd updated
        conn = db.connect()
        try:
            cost = conn.execute(
                "SELECT consultation_cost_usd FROM verdicts WHERE id = ?",
                (pre_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        _assert(abs(cost - 0.30) < 1e-9)
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)


def test_consult_rubric_missing():
    rid = f"{PREFIX}no_rubric"
    png = _make_test_png(rid)
    _seed_render(rid, png)
    rubric_dir = Path(tempfile.mkdtemp(prefix="empty_"))
    # No docs/AUDIT_RUBRICS file in the tempdir
    try:
        try:
            audit_consult.consult_render(rid, repo_root=rubric_dir)
        except audit_consult.ConsultationError as e:
            _assert("rubric" in str(e).lower())
            return
        _assert(False, "expected ConsultationError on missing rubric")
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)


def test_consult_render_missing():
    rubric_dir = _make_rubric_dir()
    try:
        try:
            audit_consult.consult_render(f"{PREFIX}ghost", repo_root=rubric_dir)
        except audit_consult.ConsultationError as e:
            _assert("not found" in str(e).lower())
            return
        _assert(False, "expected ConsultationError on missing render")
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)


def test_consult_persists_safety_refused_status():
    # v0.6 amendment 1: opted-in path so the 'weak' placeholder branch
    # (no completed inference) still has coverage.
    rid = f"{PREFIX}safety"
    png = _make_test_png(rid)
    _seed_render(rid, png)
    rubric_dir = _make_rubric_dir()
    try:
        with patch.object(vision, "call_vision", return_value=_fake_safety_refused_response()):
            result = audit_consult.consult_render(
                rid, repo_root=rubric_dir, create_verdict_if_missing=True,
            )

        _assert(len(result["consultations"]) == 1)
        _assert(result["consultations"][0]["status"] == "safety_refused")
        # Auto-created placeholder verdict (no completed inference -> 'weak')
        _assert(result["auto_created_verdict"] is True)
        detail = audit.get_render_detail(rid)
        _assert(detail["verdict"]["verdict"] == "weak")
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)


def test_consult_unknown_provider():
    rid = f"{PREFIX}unknown_p"
    png = _make_test_png(rid)
    _seed_render(rid, png)
    rubric_dir = _make_rubric_dir()
    try:
        try:
            audit_consult.consult_render(
                rid, providers=["never_exists"], repo_root=rubric_dir,
            )
        except audit_consult.ConsultationError as e:
            _assert("unknown provider" in str(e).lower())
            return
        _assert(False, "expected ConsultationError on unknown provider")
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)


def test_consult_no_verdict_no_flag_raises():
    """v0.6 amendment 1 — when no verdict exists and the caller has not
    opted in via create_verdict_if_missing, consult_render must refuse
    rather than silently auto-create a placeholder verdict on the audit
    trail. Mocks call_vision because the gate sits in step 6 (after
    provider calls); test asserts the error shape regardless."""
    rid = f"{PREFIX}no_flag"
    png = _make_test_png(rid)
    _seed_render(rid, png)
    rubric_dir = _make_rubric_dir()
    try:
        try:
            with patch.object(
                vision, "call_vision", return_value=_fake_completed_response(),
            ):
                audit_consult.consult_render(rid, repo_root=rubric_dir)
        except audit_consult.ConsultationError as e:
            msg = str(e).lower()
            _assert("verdict" in msg,
                    "error should mention the missing-verdict condition")
            _assert("create_verdict_if_missing" in msg,
                    "error should name the opt-in parameter so caller knows the fix")
            # Verdict must NOT have been created as a side effect.
            detail = audit.get_render_detail(rid)
            _assert(detail is not None, "render row should still exist")
            _assert(detail.get("verdict") is None,
                    "no verdict should be auto-created when flag is unset")
            return
        _assert(False, "expected ConsultationError when no verdict + no flag")
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)


def test_consult_session_totals_incremented():
    rid = f"{PREFIX}session"
    png = _make_test_png(rid)
    _seed_render(rid, png)
    session = audit.create_audit_session(rubric_version="1.0", mode="quick_pass")
    sid = session["id"]
    TRACKED_AUDIT_SESSION_IDS.append(sid)  # global cleanup handles it
    rubric_dir = _make_rubric_dir()
    try:
        with patch.object(vision, "call_vision", return_value=_fake_completed_response()):
            audit_consult.consult_render(
                rid, audit_session_id=sid, repo_root=rubric_dir,
                create_verdict_if_missing=True,
            )

        cost = audit.get_session_cost(sid)
        _assert(cost["total_consultations"] == 1)
        _assert(abs(cost["total_cost_usd"] - 0.30) < 1e-9)
    finally:
        shutil.rmtree(rubric_dir, ignore_errors=True)
        # Session + verdicts + ai_consultations cleaned by global cleanup()
        # at end-of-main via TRACKED_AUDIT_SESSION_IDS + render-prefix.


def main():
    cleanup()
    try:
        test_consult_happy_path_auto_creates_verdict()
        test_consult_attaches_to_existing_verdict()
        test_consult_rubric_missing()
        test_consult_render_missing()
        test_consult_persists_safety_refused_status()
        test_consult_unknown_provider()
        test_consult_no_verdict_no_flag_raises()
        test_consult_session_totals_incremented()
    finally:
        cleanup()
    print("PASS: audit_consult orchestrator — opt-in auto-create verdict, "
          "attach to existing, rubric-missing / render-missing / unknown-"
          "provider / no-verdict-no-flag errors, safety-refused persistence, "
          "session-cost rollup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
