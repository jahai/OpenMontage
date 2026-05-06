"""Audit rubric parser + loader (Phase 2 Wave B prerequisite).

Per phase2_design_notes.md v0.4 §4 parser contract.

Joseph authors the rubric at `docs/AUDIT_RUBRICS_v*.md` (canonical, AD-5
read-only to v1). This module reads + parses that file into a structured
form the audit consultation flow can pass to the vision API.

Format (markdown body + YAML front-matter; per design §4 example):

    ---
    version: "1.0"
    discipline_version: "1.0"
    applies_to_concept_types: [schematic_apparatus, cinematic_atmospheric]
    ---

    # Audit Rubric v1.0

    Optional preamble text (ignored by parser).

    ### Composition
    The framing of the render — apparatus / subject placement and
    the relationships between elements in the frame.
    - pass: composition reads at-a-glance; subject + apparatus
      relationships clear.
    - partial: composition coherent but requires study to read.
    - fail: composition incoherent or misleading.

    ### Register coherence
    [...]

Parser contract (per design §4):
  - YAML front-matter: required `version` + `discipline_version`;
    optional `applies_to_concept_types` (list of concept-type strings).
  - H3 headings (`### `) at column 0 = criterion names.
  - Body text under H3 (until next H3 or EOF) = criterion definition.
  - Bullets prefixed `pass:`, `partial:`, `fail:` (case-insensitive,
    leading whitespace permitted) = evaluation guidance per level.
  - Permissive: ordering, casing of bullet prefixes, additional H4+
    subheadings (treated as elaboration of the H3 criterion).
  - Strict: H3 as criterion anchor (no H2/H4 fallback); YAML delimited
    by `---` lines; required front-matter keys present.

Per-concept-type criteria scope: deferred. v0.1 of the rubric ships
flat criterion list applying to all concept types listed in the
front-matter. Future amendment can add per-type filtering via a
`concept_types_filter` field on individual criteria.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml


class RubricParseError(Exception):
    """Malformed rubric — front-matter or structural issues. Includes
    line context where derivable."""


# Bullet-point pattern: optional indent, '-' or '*', whitespace, then
# 'pass:'|'partial:'|'fail:' (case-insensitive), then content.
_BULLET_RE = re.compile(
    r"^\s*[-*]\s*(pass|partial|fail)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_H3_RE = re.compile(r"^###\s+(.+?)\s*$")


def parse_rubric_text(content: str) -> dict:
    """Parse rubric markdown (with YAML front-matter) into structured dict.

    Returns:
        {
            "version": str,
            "discipline_version": str,
            "applies_to_concept_types": list[str],
            "criteria": {
                "<criterion_name>": {
                    "definition": str,           # body text
                    "pass": str | None,
                    "partial": str | None,
                    "fail": str | None,
                },
                ...
            },
        }

    Raises RubricParseError on:
      - missing or malformed YAML front-matter delimiters
      - missing required front-matter keys (version, discipline_version)
      - YAML parse error (with line number from yaml.YAMLError)
    """
    # Step 1: extract YAML front-matter delimited by --- lines.
    # Front-matter MUST start at column 0 line 1; design notes §4 explicit.
    if not content.lstrip("﻿").startswith("---"):
        raise RubricParseError(
            "rubric must start with YAML front-matter (---) at line 1"
        )

    # Strip BOM if present.
    if content.startswith("﻿"):
        content = content[1:]

    # Find the closing --- delimiter. Must be on its own line.
    lines = content.split("\n")
    if lines[0].strip() != "---":
        raise RubricParseError(
            f"front-matter open delimiter (---) not found at line 1; got {lines[0]!r}"
        )

    closing_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_idx = i
            break
    if closing_idx is None:
        raise RubricParseError(
            "front-matter has no closing --- delimiter"
        )

    yaml_text = "\n".join(lines[1:closing_idx])
    body_lines = lines[closing_idx + 1:]

    try:
        front_matter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        raise RubricParseError(f"malformed YAML front-matter: {e}")

    if not isinstance(front_matter, dict):
        raise RubricParseError(
            f"YAML front-matter must be a dict, got {type(front_matter).__name__}"
        )

    for required_key in ("version", "discipline_version"):
        if required_key not in front_matter:
            raise RubricParseError(
                f"YAML front-matter missing required key: {required_key!r}"
            )

    # Step 2: walk body lines, accumulating criteria by H3 boundary.
    criteria: dict[str, dict] = {}
    current_name: Optional[str] = None
    current_definition_lines: list[str] = []
    current_eval: dict[str, Optional[str]] = {"pass": None, "partial": None, "fail": None}

    def flush() -> None:
        nonlocal current_name, current_definition_lines, current_eval
        if current_name is None:
            return
        # Definition is body text minus the bullet lines (which fed
        # current_eval). Strip trailing blank lines.
        definition = "\n".join(current_definition_lines).strip()
        criteria[current_name] = {
            "definition": definition,
            "pass": current_eval["pass"],
            "partial": current_eval["partial"],
            "fail": current_eval["fail"],
        }
        current_name = None
        current_definition_lines = []
        current_eval = {"pass": None, "partial": None, "fail": None}

    for line in body_lines:
        h3_match = _H3_RE.match(line)
        if h3_match:
            flush()
            current_name = h3_match.group(1).strip()
            continue
        if current_name is None:
            # Pre-criterion content (preamble, H1/H2 headings) — ignored.
            continue
        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            level = bullet_match.group(1).lower()
            text = bullet_match.group(2).strip()
            current_eval[level] = text
            continue
        # Definition body line.
        current_definition_lines.append(line)

    flush()  # final criterion

    return {
        "version": str(front_matter["version"]),
        "discipline_version": str(front_matter["discipline_version"]),
        "applies_to_concept_types": list(
            front_matter.get("applies_to_concept_types", [])
        ),
        "criteria": criteria,
    }


def parse_rubric_file(path: Path | str) -> dict:
    """Read rubric file from disk and parse. See parse_rubric_text for shape."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"rubric file not found: {p}")
    return parse_rubric_text(p.read_text(encoding="utf-8"))


def find_latest_rubric(docs_dir: Path | str) -> Optional[Path]:
    """Return the path of the highest-version rubric in docs_dir.

    Looks for files matching `AUDIT_RUBRICS_v*.md`. Version is parsed
    from the `_v<MAJOR>_<MINOR>.md` suffix; lexical sort within (major,
    minor) tuple. Returns None if no matching files exist.
    """
    d = Path(docs_dir)
    if not d.exists():
        return None
    candidates: list[tuple[tuple[int, int], Path]] = []
    pattern = re.compile(r"^AUDIT_RUBRICS_v(\d+)_(\d+)\.md$", re.IGNORECASE)
    for p in d.iterdir():
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            candidates.append(((major, minor), p))
    if not candidates:
        return None
    candidates.sort(reverse=True)  # highest version first
    return candidates[0][1]


def load_active_rubric(repo_root: Path | str) -> Optional[dict]:
    """High-level loader: find latest rubric in `docs/`, parse, return.

    Returns None if no rubric exists yet (Wave A non-AI mode case).
    Audit consultation flow checks for None and falls back to manual
    verdict-only mode.
    """
    docs_dir = Path(repo_root) / "projects" / "latent_systems" / "docs"
    rubric_path = find_latest_rubric(docs_dir)
    if rubric_path is None:
        return None
    return parse_rubric_file(rubric_path)
