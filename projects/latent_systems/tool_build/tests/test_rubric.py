#!/usr/bin/env python3
"""Phase 2 Wave B prerequisite — rubric parser tests.

Exercises rubric.parse_rubric_text() + parse_rubric_file() against
fixture rubric strings inline. Per design notes §4 parser contract:
strict on YAML delimiters + H3 anchors; permissive on whitespace,
casing, ordering of pass/partial/fail bullets, additional H4+
elaboration.

Run: python tool_build/tests/test_rubric.py
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402, F401  (Pattern #3: import db for codec setup)
from rubric import (  # noqa: E402
    RubricParseError, parse_rubric_text, parse_rubric_file,
    find_latest_rubric, load_active_rubric,
)


VALID_RUBRIC = """\
---
version: "1.0"
discipline_version: "1.0"
applies_to_concept_types: [schematic_apparatus, cinematic_atmospheric]
---

# Audit Rubric v1.0

Optional preamble paragraph that the parser ignores.

### Composition
The framing of the render — apparatus / subject placement and
relationships between elements in the frame.
- pass: composition reads at-a-glance; subject + apparatus relationships clear.
- partial: composition coherent but requires study to read.
- fail: composition incoherent or misleading.

### Register coherence
Whether the render's tonal/period vocabulary holds across the frame.
- pass: register holds at 100%; nothing breaks the register.
- partial: register mostly holds; one or two minor breaks.
- fail: register breaks; mixed-period or anachronistic elements.

### Apparatus fidelity
Schematic-precision rendering of apparatus elements.
- pass: every apparatus element legible + period-correct.
- partial: most legible; one or two ambiguous.
- fail: apparatus indistinct or wrong-era.
"""


def _assert(cond, msg="assertion failed"):
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def test_valid_rubric_basic():
    rubric = parse_rubric_text(VALID_RUBRIC)
    _assert(rubric["version"] == "1.0")
    _assert(rubric["discipline_version"] == "1.0")
    _assert("schematic_apparatus" in rubric["applies_to_concept_types"])
    _assert(len(rubric["criteria"]) == 3,
            f"expected 3 criteria, got {len(rubric['criteria'])}")


def test_criterion_definition_and_evaluation():
    rubric = parse_rubric_text(VALID_RUBRIC)
    comp = rubric["criteria"]["Composition"]
    _assert("framing of the render" in comp["definition"])
    _assert(comp["pass"].startswith("composition reads at-a-glance"))
    _assert(comp["partial"].startswith("composition coherent but"))
    _assert(comp["fail"].startswith("composition incoherent"))


def test_permissive_bullet_casing():
    """Bullet prefix matching is case-insensitive per parser contract."""
    content = """\
---
version: "1.0"
discipline_version: "1.0"
---

### Composition
Body.
- PASS: upper case pass
- Partial: title case partial
- fail: lower case fail
"""
    rubric = parse_rubric_text(content)
    _assert(rubric["criteria"]["Composition"]["pass"] == "upper case pass")
    _assert(rubric["criteria"]["Composition"]["partial"] == "title case partial")
    _assert(rubric["criteria"]["Composition"]["fail"] == "lower case fail")


def test_permissive_bullet_ordering():
    """pass/partial/fail can appear in any order under H3."""
    content = """\
---
version: "1.0"
discipline_version: "1.0"
---

### Composition
- fail: F text
- pass: P text
- partial: PA text
"""
    rubric = parse_rubric_text(content)
    c = rubric["criteria"]["Composition"]
    _assert(c["pass"] == "P text")
    _assert(c["partial"] == "PA text")
    _assert(c["fail"] == "F text")


def test_h4_elaboration_treated_as_definition():
    """H4 subheadings under an H3 are part of the criterion's definition,
    not new criteria."""
    content = """\
---
version: "1.0"
discipline_version: "1.0"
---

### Composition
Top-level definition.

#### Subtopic A
Elaboration.

#### Subtopic B
More elaboration.

- pass: ok
"""
    rubric = parse_rubric_text(content)
    _assert(len(rubric["criteria"]) == 1, "H4 should not create a new criterion")
    defn = rubric["criteria"]["Composition"]["definition"]
    _assert("Top-level definition" in defn)
    _assert("Subtopic A" in defn)
    _assert("Subtopic B" in defn)


def test_missing_front_matter():
    content = """\
# Rubric without front-matter
### Composition
- pass: ok
"""
    try:
        parse_rubric_text(content)
    except RubricParseError as e:
        _assert("front-matter" in str(e).lower())
        return
    _assert(False, "expected RubricParseError on missing front-matter")


def test_missing_closing_delimiter():
    content = """\
---
version: "1.0"
discipline_version: "1.0"

### Composition
"""
    try:
        parse_rubric_text(content)
    except RubricParseError as e:
        _assert("closing" in str(e).lower())
        return
    _assert(False, "expected RubricParseError on missing closing ---")


def test_missing_required_key():
    content = """\
---
version: "1.0"
---

### Composition
- pass: ok
"""
    try:
        parse_rubric_text(content)
    except RubricParseError as e:
        _assert("discipline_version" in str(e))
        return
    _assert(False, "expected RubricParseError on missing discipline_version")


def test_malformed_yaml():
    content = """\
---
version: "1.0
discipline_version: "1.0"
---

### Composition
- pass: ok
"""
    try:
        parse_rubric_text(content)
    except RubricParseError as e:
        _assert("yaml" in str(e).lower() or "malformed" in str(e).lower())
        return
    _assert(False, "expected RubricParseError on malformed YAML")


def test_criterion_without_evaluation_bullets():
    """A criterion with just definition body and no pass/partial/fail
    bullets parses successfully with all three None — design notes
    parser contract: 'criteria-without-grading-scale; AI consultation
    given description but no structured evaluation guidance.'"""
    content = """\
---
version: "1.0"
discipline_version: "1.0"
---

### Composition
Just a description, no grading scale yet.
"""
    rubric = parse_rubric_text(content)
    c = rubric["criteria"]["Composition"]
    _assert("Just a description" in c["definition"])
    _assert(c["pass"] is None)
    _assert(c["partial"] is None)
    _assert(c["fail"] is None)


def test_no_criteria_returns_empty_dict():
    """Front-matter only, no H3 headings."""
    content = """\
---
version: "1.0"
discipline_version: "1.0"
---

# Audit Rubric v1.0

Just a preamble; no criteria yet.
"""
    rubric = parse_rubric_text(content)
    _assert(rubric["criteria"] == {})


def test_parse_rubric_file_roundtrip():
    """parse_rubric_file reads from disk + parses (delegates to parse_rubric_text)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "AUDIT_RUBRICS_v1_0.md"
        path.write_text(VALID_RUBRIC, encoding="utf-8")
        rubric = parse_rubric_file(path)
        _assert(rubric["version"] == "1.0")
        _assert("Composition" in rubric["criteria"])


def test_find_latest_rubric():
    """Highest-version rubric in a directory wins."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        # Create three rubric files
        (d / "AUDIT_RUBRICS_v1_0.md").write_text(VALID_RUBRIC, encoding="utf-8")
        (d / "AUDIT_RUBRICS_v1_2.md").write_text(VALID_RUBRIC, encoding="utf-8")
        (d / "AUDIT_RUBRICS_v2_0.md").write_text(VALID_RUBRIC, encoding="utf-8")
        # And some unrelated files
        (d / "OTHER.md").write_text("# unrelated", encoding="utf-8")
        latest = find_latest_rubric(d)
        _assert(latest is not None)
        _assert(latest.name == "AUDIT_RUBRICS_v2_0.md",
                f"expected v2_0 to win, got {latest.name}")


def test_find_latest_rubric_none_when_empty():
    with tempfile.TemporaryDirectory() as tmp:
        _assert(find_latest_rubric(tmp) is None)


def test_load_active_rubric_none_when_no_docs():
    """load_active_rubric returns None when no rubric file present —
    Wave A non-AI mode falls back gracefully."""
    with tempfile.TemporaryDirectory() as tmp:
        # Set up dir structure but no rubric file
        (Path(tmp) / "projects" / "latent_systems" / "docs").mkdir(parents=True)
        _assert(load_active_rubric(tmp) is None)


def main():
    test_valid_rubric_basic()
    test_criterion_definition_and_evaluation()
    test_permissive_bullet_casing()
    test_permissive_bullet_ordering()
    test_h4_elaboration_treated_as_definition()
    test_missing_front_matter()
    test_missing_closing_delimiter()
    test_missing_required_key()
    test_malformed_yaml()
    test_criterion_without_evaluation_bullets()
    test_no_criteria_returns_empty_dict()
    test_parse_rubric_file_roundtrip()
    test_find_latest_rubric()
    test_find_latest_rubric_none_when_empty()
    test_load_active_rubric_none_when_no_docs()
    print("PASS: rubric — parse_rubric_text contract + permissive cases + "
          "error cases + file/loader plumbing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
