"""Filesystem walker — pre_v1 marker enumeration.

Per phase1_design_notes.md Section 4: enumerates existing canonical
renders and seeds them into state.db with discipline_version='pre_v1'.

Scope (Phase 1):
    - shared/<dir>/run_<date>/*.{png,mp4,mp3}  → renders rows
    - shared/<dir>/winners/*.{png,mp4,mp3}      → renders + hero_promotions
    - ep1/<section>/*.{png,mp4,mp3}             → renders rows

Out of scope (Phase 1 schema doesn't define tables for these):
    - ep1/<section>/NOTES.md
    - docs/*ARCHITECTURE*.md
    Phase 3 will extend the schema to cover NOTES.md state and
    architecture-doc references.

Coexistence: walker only WRITES to tool_build/_data/ (state.db rows
+ _data/renders/<id>.yaml representations). It only READS from the
canonical paths. AD-3 forward-only: no sidecar files on existing
canonical artifacts; no prompt_id binding (the originating prompts
were never on filesystem).

Idempotency: re-runs are no-ops on (canonical_hash, filepath) match.
Files that change content under the same path produce a new render
row on next walk; old row is preserved (Phase 1 doesn't migrate).
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import yaml

import db


from constants import DISCIPLINE_PRE_V1, SUPPORTED_SCHEMA_VERSIONS

CANONICAL_ROOTS = ("shared", "ep1")
RENDER_EXTENSIONS = (".png", ".mp4", ".mp3")
HERO_STATUS_PRE_V1 = "pre_v1_hero"

# Filename classifiers.
#
# Phase 1 baseline: MJ_RE / GPT_RE / KLING_RE — strict patterns matching
# the canonical filename shapes from each tool's native download.
#
# Phase 2 Day 1 extension (v0.3 design notes amendment): broader patterns
# to recover tool attribution from filenames Joseph reorganized after
# download. Day 1 inspection of 1434 unknown_image rows showed:
#   - 51%+ are video frame extracts (frame_NNNN.png etc.) — new
#     `frame_extract` tool category
#   - 6%+ are MJ outputs whose nycwillow_ prefix was renamed away but
#     retain the `_mj_<hex>_<variant>.png` infix
#   - small populations of GPT, Flux, and Kontext outputs caught by
#     case-insensitive markers
# Pattern check order matters: strict patterns first (they carry the
# most signal — variant numbers, structured hashes), broader markers
# next, frame-extract last, then extension-only fallbacks.
MJ_RE = re.compile(r"^nycwillow_(.+)_([a-f0-9]{8})-[a-f0-9-]+_([0-3])\.png$")
MJ_INFIX_RE = re.compile(r"_mj_[a-f0-9]{8}_([0-3])\.png$", re.IGNORECASE)
GPT_RE = re.compile(r"^ChatGPT Image .+\.png$")
GPT_INFIX_RE = re.compile(r"(gpt|chatgpt|dalle)", re.IGNORECASE)
KLING_RE = re.compile(r"^kling_\d{8}_.+\.mp4$")
FLUX_RE = re.compile(r"(flux|kontext)", re.IGNORECASE)
FRAME_RE = re.compile(
    # frame_NNNN.png | fNN_NN.png | t_X.X.png | _final_tX.X.png
    r"^(?:"
    r"frame_\d+"           # frame_NNNN
    r"|f\d+_\d+"           # fNN_NN
    r"|_?final_t[\d.]+"    # _final_tX.X or final_tX.X
    r"|t_?[\d.]+"          # t_X.X or tX.X
    r")\.png$",
    re.IGNORECASE,
)


def classify(filename: str) -> tuple[str, Optional[int]]:
    """Return (tool, variant). Tool is one of: midjourney, gpt_image_2,
    kling, flux, frame_extract, video, audio, unknown_image, unknown.
    Variant is parsed from MJ filenames (both strict and infix); None
    for other tools.

    Order of checks (most-specific first):
      1. MJ strict (nycwillow_<...>_<hash>-<uuid>_<variant>.png)
      2. MJ infix (..._mj_<hex8>_<variant>.png) — Joseph-renamed MJ
      3. GPT strict (ChatGPT Image YYYY-MM-DD HH-MM-SS.png)
      4. Kling strict (kling_YYYYMMDD_*.mp4)
      5. GPT infix (case-insensitive 'gpt'|'chatgpt'|'dalle' anywhere)
      6. Flux family (case-insensitive 'flux'|'kontext' anywhere)
      7. Frame extract (frame_NNNN.png, fNN_NN.png, t_X.X.png variants)
      8. Extension fallback (.mp4 -> video, .mp3 -> audio, .png -> unknown_image)
    """
    m = MJ_RE.match(filename)
    if m:
        return ("midjourney", int(m.group(3)))
    m = MJ_INFIX_RE.search(filename)
    if m:
        return ("midjourney", int(m.group(1)))
    if GPT_RE.match(filename):
        return ("gpt_image_2", None)
    if KLING_RE.match(filename):
        return ("kling", None)
    if GPT_INFIX_RE.search(filename):
        return ("gpt_image_2", None)
    if FLUX_RE.search(filename):
        return ("flux", None)
    if FRAME_RE.match(filename):
        return ("frame_extract", None)
    lower = filename.lower()
    if lower.endswith(".mp4"):
        return ("video", None)
    if lower.endswith(".mp3"):
        return ("audio", None)
    if lower.endswith(".png"):
        return ("unknown_image", None)
    return ("unknown", None)


def sha256_of(path: Path, chunk_size: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk_size)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def is_hero_path(rel_path: Path) -> bool:
    """A render is a pre_v1 hero if its path contains a /winners/ segment."""
    return "winners" in rel_path.parts


def iter_render_files(latent_systems_dir: Path) -> Iterable[Path]:
    """Yield absolute paths of canonical render files under latent_systems.

    Note: assumes CANONICAL_ROOTS are disjoint paths. Phase 3 walker
    extension (NOTES.md, architecture docs) must preserve this — adding
    a root that overlaps an existing root would cause duplicate yields.
    """
    for root in CANONICAL_ROOTS:
        root_dir = latent_systems_dir / root
        if not root_dir.exists():
            continue
        for ext in RENDER_EXTENSIONS:
            yield from root_dir.rglob(f"*{ext}")
    # TODO Phase 3: NOTES.md and architecture-doc enumeration when
    # notes_md_state and doc_set tables land per Section 2 schema
    # extension. Walker scope today is renders only because Phase 1
    # schema doesn't define tables for those artifact types.


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def render_yaml(
    *, render_id: str, rel_path: str, filename: str, canonical_hash: str,
    tool: str, variant: Optional[int], hero_status: Optional[str],
) -> dict:
    return {
        "id": render_id,
        "discipline_version": DISCIPLINE_PRE_V1,
        "filename": filename,
        "filepath": rel_path,
        "canonical_hash": canonical_hash,
        "tool": tool,
        "variant": variant,
        "hero_status": hero_status,
        "created": iso_now(),
        "notes": (
            "Enumerated by Phase 1 walker. No originating prompt_id "
            "(AD-3 forward-only)."
        ),
    }


def schema_check(conn: sqlite3.Connection) -> None:
    """Refuse to walk if schema_version is missing or unsupported.

    Reads SUPPORTED_SCHEMA_VERSIONS from constants — single source of
    truth across migrations. When a new migration lands, add the new
    version to that set in constants.py.
    """
    cur = conn.execute("SELECT value FROM app_meta WHERE key='schema_version'")
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("app_meta.schema_version missing; run --migrate-schema first.")
    if row[0] not in SUPPORTED_SCHEMA_VERSIONS:
        raise RuntimeError(
            f"unsupported schema_version='{row[0]}' (walker supports {sorted(SUPPORTED_SCHEMA_VERSIONS)}). "
            f"Run --migrate-schema if behind, or update SUPPORTED_SCHEMA_VERSIONS if ahead."
        )


def existing_render(conn: sqlite3.Connection, canonical_hash: str, filepath: str) -> Optional[str]:
    cur = conn.execute(
        "SELECT id FROM renders WHERE canonical_hash = ? AND filepath = ?",
        (canonical_hash, filepath),
    )
    row = cur.fetchone()
    return row[0] if row else None


def existing_hero(conn: sqlite3.Connection, render_id: str) -> Optional[str]:
    cur = conn.execute(
        "SELECT id FROM hero_promotions WHERE render_id = ?",
        (render_id,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def insert_render(
    conn: sqlite3.Connection, *, render_id: str, filename: str, filepath: str,
    canonical_hash: str, tool: str, variant: Optional[int],
    hero_status: Optional[str], yaml_path: str, created: str,
) -> None:
    conn.execute(
        """
        INSERT INTO renders (
            id, attempt_id, prompt_id, filename, filepath,
            download_hash, canonical_hash, tool, variant, hero_status,
            discipline_version, yaml_path, created
        ) VALUES (?, NULL, NULL, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
        """,
        (render_id, filename, filepath, canonical_hash, tool, variant,
         hero_status, DISCIPLINE_PRE_V1, yaml_path, created),
    )


def insert_hero(
    conn: sqlite3.Connection, *, render_id: str, hero_filepath: str,
    yaml_path: str, created: str,
) -> None:
    hero_id = f"hero_{render_id}"  # stable ID derived from render
    conn.execute(
        """
        INSERT INTO hero_promotions (
            id, render_id, hero_filepath, reversed_at, reversed_reason,
            discipline_version, yaml_path, created
        ) VALUES (?, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        (hero_id, render_id, hero_filepath, DISCIPLINE_PRE_V1, yaml_path, created),
    )


def walk(
    *, repo_root: Path, dry_run: bool = False, verbose: bool = False,
) -> dict:
    """Enumerate canonical renders into state.db. Returns summary dict.

    Per-file commit: each successful (render row + optional hero row +
    YAML write) commits independently. Bounds partial-state risk to a
    single file if walker errors mid-run. Idempotent rerun cleans up
    any partial state from previous error.
    """
    latent_systems_dir = repo_root / "projects" / "latent_systems"
    renders_dir = db.DATA_DIR / "renders"

    if not dry_run:
        renders_dir.mkdir(parents=True, exist_ok=True)

    conn = db.connect()
    try:
        schema_check(conn)

        summary = {
            "walked": 0, "new_render": 0, "skipped_existing": 0,
            "new_hero": 0, "skipped_hero": 0, "errors": 0,
        }

        for abs_path in iter_render_files(latent_systems_dir):
            summary["walked"] += 1
            try:
                rel_to_repo = abs_path.relative_to(repo_root).as_posix()
                filename = abs_path.name
                canonical_hash = sha256_of(abs_path)
                # ID derived from (hash, filepath) so content-identical files
                # at different paths (e.g. render + its winners/ copy) get
                # distinct render rows. Same (content, path) → same id.
                render_id = hashlib.sha256(
                    f"{canonical_hash}|{rel_to_repo}".encode("utf-8")
                ).hexdigest()[:16]

                if existing_render(conn, canonical_hash, rel_to_repo):
                    summary["skipped_existing"] += 1
                    if verbose:
                        print(f"[walker] skip (already recorded): {rel_to_repo}")
                    continue

                tool, variant = classify(filename)
                hero_status = HERO_STATUS_PRE_V1 if is_hero_path(
                    abs_path.relative_to(latent_systems_dir)
                ) else None
                yaml_rel = f"projects/latent_systems/tool_build/_data/renders/{render_id}.yaml"
                yaml_abs = renders_dir / f"{render_id}.yaml"
                created = iso_now()

                payload = render_yaml(
                    render_id=render_id, rel_path=rel_to_repo, filename=filename,
                    canonical_hash=canonical_hash, tool=tool, variant=variant,
                    hero_status=hero_status,
                )

                if dry_run:
                    summary["new_render"] += 1
                    if hero_status:
                        summary["new_hero"] += 1
                    if verbose:
                        print(f"[walker] DRY: {rel_to_repo} ({tool}, hero={bool(hero_status)})")
                    continue

                # YAML write before SQL insert: a failed YAML write leaves
                # no state.db row. Reverse order would create an orphan row
                # pointing to a missing file — worse failure shape.
                with yaml_abs.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(payload, f, sort_keys=False,
                                   default_flow_style=False, allow_unicode=True)

                insert_render(
                    conn, render_id=render_id, filename=filename,
                    filepath=rel_to_repo, canonical_hash=canonical_hash,
                    tool=tool, variant=variant, hero_status=hero_status,
                    yaml_path=yaml_rel, created=created,
                )
                summary["new_render"] += 1

                if hero_status and not existing_hero(conn, render_id):
                    insert_hero(
                        conn, render_id=render_id, hero_filepath=rel_to_repo,
                        yaml_path=yaml_rel, created=created,
                    )
                    summary["new_hero"] += 1

                # Per-file commit: bounds partial-state risk on mid-run error.
                conn.commit()

                if verbose:
                    print(f"[walker] new: {rel_to_repo} ({tool}, hero={bool(hero_status)})")

            except (OSError, ValueError, sqlite3.Error) as e:
                summary["errors"] += 1
                print(f"[walker] ERROR on {abs_path}: {e}", file=sys.stderr)
                # Roll back any uncommitted state for this file's transaction.
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass

        return summary
    finally:
        conn.close()


def reclassify_unknowns(*, dry_run: bool = False, verbose: bool = False) -> dict:
    """Phase 2 Day 1 migration: re-run classify() against existing rows
    where tool='unknown_image' and update both state.db + YAML when the
    extended classifier produces a more-specific tool.

    Per phase2_design_notes.md v0.3 §6: this exists because the Phase 1
    walker's classifier was too narrow — recovering ~70-75% of the 1434
    pre_v1 renders currently marked unknown_image. Filename-pattern only;
    filepath heuristics deferred to Phase 3.

    YAML write before SQL update — same pattern as walk(): a failed YAML
    write leaves state.db unchanged. Reverse order would create a row
    pointing at a stale-tool YAML.

    Returns a summary dict: walked, reclassified counts by new tool,
    unchanged count, errors.
    """
    summary: dict = {
        "walked": 0,
        "reclassified": {},  # new_tool -> count
        "unchanged": 0,
        "errors": 0,
    }

    conn = db.connect()
    try:
        schema_check(conn)

        # Snapshot the rows up front; we'll iterate without holding the
        # cursor (we issue UPDATE statements during the loop).
        rows = conn.execute(
            "SELECT id, filename, filepath, variant, yaml_path "
            "FROM renders WHERE tool = 'unknown_image'"
        ).fetchall()

        for render_id, filename, filepath, _old_variant, yaml_rel in rows:
            summary["walked"] += 1
            try:
                new_tool, new_variant = classify(filename)
                if new_tool == "unknown_image":
                    summary["unchanged"] += 1
                    continue

                if not dry_run:
                    # 1. Update YAML (source of truth per AD-5).
                    yaml_abs = db.TOOL_BUILD_DIR.parent.parent.parent / yaml_rel
                    if not yaml_abs.exists():
                        # Try resolving via DATA_DIR layout if yaml_path
                        # was stored as repo-relative (the walker writes
                        # repo-relative paths).
                        yaml_abs = db.DATA_DIR / "renders" / f"{render_id}.yaml"
                    with yaml_abs.open("r", encoding="utf-8") as f:
                        payload = yaml.safe_load(f) or {}
                    payload["tool"] = new_tool
                    payload["variant"] = new_variant
                    # Audit-trail note: when this row was reclassified
                    # and from what.
                    prior_note = payload.get("notes", "") or ""
                    reclass_note = (
                        f"Reclassified by Phase 2 Day 1 walker pattern "
                        f"extension on {iso_now()}: was unknown_image, "
                        f"now {new_tool}."
                    )
                    payload["notes"] = (
                        prior_note + "\n" + reclass_note if prior_note
                        else reclass_note
                    )
                    with yaml_abs.open("w", encoding="utf-8") as f:
                        yaml.safe_dump(
                            payload, f, sort_keys=False,
                            default_flow_style=False, allow_unicode=True,
                        )

                    # 2. Update state.db (cache).
                    with conn:
                        conn.execute(
                            "UPDATE renders SET tool = ?, variant = ? WHERE id = ?",
                            (new_tool, new_variant, render_id),
                        )

                summary["reclassified"][new_tool] = (
                    summary["reclassified"].get(new_tool, 0) + 1
                )

                if verbose:
                    print(
                        f"[reclassify] {filepath}: unknown_image -> "
                        f"{new_tool}{f' v={new_variant}' if new_variant is not None else ''}"
                    )

            except (OSError, ValueError, sqlite3.Error, yaml.YAMLError) as e:
                summary["errors"] += 1
                print(f"[reclassify] ERROR on {filepath}: {e}", file=sys.stderr)
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass

        return summary
    finally:
        conn.close()


if __name__ == "__main__":
    # Direct invocation requires git on PATH (used to locate the repo
    # root). Phase 1 acceptable; Phase 2 could fall back to walking
    # from this file's path if git is unavailable.
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="enumerate without writing to state.db or yaml files")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--reclassify-unknowns", action="store_true",
        help="Phase 2 Day 1 migration: re-run classify() against rows "
             "where tool='unknown_image' and update tool field if the "
             "extended classifier produces a more-specific value. "
             "Combine with --dry-run to preview without writing.",
    )
    args = parser.parse_args()

    if args.reclassify_unknowns:
        summary = reclassify_unknowns(dry_run=args.dry_run, verbose=args.verbose)
        total_recl = sum(summary["reclassified"].values())
        total_walked = summary["walked"]
        rate = (100.0 * total_recl / total_walked) if total_walked else 0.0
        print(f"[reclassify] summary: walked={total_walked} "
              f"reclassified={total_recl} ({rate:.1f}%) "
              f"unchanged={summary['unchanged']} errors={summary['errors']}")
        if summary["reclassified"]:
            print("[reclassify] by new tool:")
            for tool, count in sorted(summary["reclassified"].items(), key=lambda x: -x[1]):
                print(f"  {tool:20s} {count}")
        sys.exit(1 if summary["errors"] else 0)

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[walker] ERROR: git CLI required for direct invocation ({e})", file=sys.stderr)
        sys.exit(2)
    root = Path(out.stdout.strip())

    summary = walk(repo_root=root, dry_run=args.dry_run, verbose=args.verbose)
    print(f"[walker] summary: {summary}")
    sys.exit(1 if summary["errors"] else 0)
