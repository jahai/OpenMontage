"""Seed loader — copies version-controlled seed YAMLs from tool_build/seeds/
into _data/<artifact_type>/ at --init time, registers them in state.db.

Day 11: ships MJ tool-grammar seed (Section 3 verbatim). Future seeds
(GPT Image 2, Kling, ElevenLabs tool-grammar configs) land in Phase 2
after Phase 1 usage informs them.

Idempotent: re-running --init won't overwrite existing _data/ copies if
they already match the seed. Joseph can edit _data/ copies in place
(they're the source of truth per AD-5); seed re-runs only fire if the
_data/ copy is missing.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

import db


SCRIPT_DIR = Path(__file__).resolve().parent
SEEDS_DIR = SCRIPT_DIR / "seeds"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_tool_grammar_seed(tool: str) -> dict:
    """Copy seeds/<tool>.yaml into _data/tool_grammar_configs/<tool>.yaml
    if not already present, then register/update the state.db row.

    Returns summary dict: {tool, action, yaml_path, discipline_version}.
    """
    seed_path = SEEDS_DIR / f"{tool}.yaml"
    if not seed_path.exists():
        return {"tool": tool, "action": "skip_no_seed",
                "reason": f"no seed at {seed_path}"}

    target_dir = db.DATA_DIR / "tool_grammar_configs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{tool}.yaml"

    if target_path.exists():
        action = "skip_already_present"
    else:
        shutil.copy2(seed_path, target_path)
        action = "copied_from_seed"

    # Parse to get discipline_version for state.db row.
    data = yaml.safe_load(target_path.read_text(encoding="utf-8")) or {}
    discipline_version = data.get("discipline_version", "1.0")
    yaml_rel = f"projects/latent_systems/tool_build/_data/tool_grammar_configs/{tool}.yaml"
    now = _iso_now()

    conn = db.connect()
    try:
        with conn:
            existing = conn.execute(
                "SELECT tool FROM tool_grammar_configs WHERE tool = ?", (tool,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE tool_grammar_configs
                    SET discipline_version = ?, yaml_path = ?, last_updated = ?
                    WHERE tool = ?
                    """,
                    (discipline_version, yaml_rel, now, tool),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tool_grammar_configs (
                        tool, discipline_version, yaml_path, last_updated
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (tool, discipline_version, yaml_rel, now),
                )
    finally:
        conn.close()

    return {
        "tool": tool, "action": action,
        "yaml_path": yaml_rel,
        "discipline_version": discipline_version,
    }


def load_all_seeds() -> list[dict]:
    """Load every *.yaml under seeds/ as a tool-grammar config.
    Phase 1 has just mj.yaml; Phase 2 will add gpt_image_2, kling, elevenlabs.
    """
    if not SEEDS_DIR.exists():
        return []
    summaries = []
    for seed in sorted(SEEDS_DIR.glob("*.yaml")):
        tool = seed.stem
        summaries.append(load_tool_grammar_seed(tool))
    return summaries


def get_tool_grammar_yaml(tool: str) -> str:
    """Return the raw YAML text for a tool's grammar config. Used by
    dispatcher.draft_via_api as the system-prompt payload."""
    target_path = db.DATA_DIR / "tool_grammar_configs" / f"{tool}.yaml"
    if not target_path.exists():
        raise FileNotFoundError(
            f"tool-grammar config missing for '{tool}' at {target_path}; "
            f"run --init or call load_tool_grammar_seed('{tool}') first."
        )
    return target_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    summaries = load_all_seeds()
    print(f"Loaded {len(summaries)} seed(s):")
    for s in summaries:
        print(f"  {s}")
    sys.exit(0)
