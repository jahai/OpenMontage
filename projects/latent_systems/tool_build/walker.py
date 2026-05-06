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

# Filename classifiers — light Phase 1 implementations of router_config
# patterns. Extend in Phase 2 when GPT Image 2 / Kling specifics matter.
MJ_RE = re.compile(r"^nycwillow_(.+)_([a-f0-9]{8})-[a-f0-9-]+_([0-3])\.png$")
GPT_RE = re.compile(r"^ChatGPT Image .+\.png$")
KLING_RE = re.compile(r"^kling_\d{8}_.+\.mp4$")


def classify(filename: str) -> tuple[str, Optional[int]]:
    """Return (tool, variant). Tool is one of: midjourney, gpt_image_2,
    kling, video, audio, unknown. Variant is parsed from MJ filenames."""
    m = MJ_RE.match(filename)
    if m:
        return ("midjourney", int(m.group(3)))
    if GPT_RE.match(filename):
        return ("gpt_image_2", None)
    if KLING_RE.match(filename):
        return ("kling", None)
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
    args = parser.parse_args()

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
