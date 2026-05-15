"""Per-section rough-cut player override persistence (Day 4 of Phase 3 sprint).

Persists manual sequence reorders, per-asset duration overrides, and
inter-paragraph gap config as YAML sidecars at:
    _data/rough_cut_overrides/<section>.yaml

Per Joseph's Q2 confirmation (2026-05-14) — YAML sidecar approach over
SQL table, fits AD-5 filesystem-canonical pattern. Per-section file
scope keeps each section's overrides independently editable + diff-able
without touching neighbors. The cross-section flow-eval endpoint
(/video/{ep_id}/roughcut_full, Day 4 also) reads a separate top-level
_episode.yaml if present — out of scope for this module.

Schema (all fields optional; missing file => no-op apply):

    manual_sequence:
      - <asset_id>
      - <asset_id>
    per_asset_duration_seconds:
      <asset_id>: <float>
    inter_paragraph_gap_seconds: <float>   # default DEFAULT_INTER_PARAGRAPH_GAP_SECONDS

apply_overrides() is the integration point with roughcut.build_roughcut_data():
  - reorders assets by manual_sequence (drops unknown IDs, preserves
    leftover assets at the end in original order — defensive, so a stale
    sequence missing a new render doesn't hide that render entirely)
  - stamps each asset with override_duration_seconds when an override exists
  - returns the resolved inter_paragraph_gap_seconds
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

import db


DEFAULT_INTER_PARAGRAPH_GAP_SECONDS = 0.5  # Q4 confirmation 2026-05-14


def _overrides_dir() -> Path:
    return db.DATA_DIR / "rough_cut_overrides"


def _overrides_path(section: str) -> Path:
    return _overrides_dir() / f"{section}.yaml"


def _episode_overrides_path(ep_id: str) -> Path:
    """Episode-level overrides file. Underscore-prefix keeps it from
    colliding with any section_id namespace; ep_id suffix scales when
    EP2+ exist."""
    return _overrides_dir() / f"_episode_{ep_id}.yaml"


def load_episode_overrides(ep_id: str) -> dict:
    """Load episode-level overrides (section_order, etc.). Returns {}
    if no file exists.

    Schema:
        section_order:
          - cold_open
          - h1_hook
          ...
    """
    path = _episode_overrides_path(ep_id)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return {}
    return data


def save_episode_overrides(ep_id: str, overrides: dict) -> None:
    """Persist episode-level overrides via tmp + atomic rename."""
    path = _episode_overrides_path(ep_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(overrides, f, sort_keys=False,
                       default_flow_style=False, allow_unicode=True)
    tmp.replace(path)


def load_overrides(section: str) -> dict:
    """Load overrides for a section. Returns {} if no file exists.

    Robust to empty / partially-populated files — missing keys are
    simply absent from the returned dict.
    """
    path = _overrides_path(section)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return {}
    return data


def save_overrides(section: str, overrides: dict) -> None:
    """Write overrides for a section via tmp + atomic rename.

    Mirrors audio_assets._write_audio_asset_yaml's atomicity guarantee
    so partial writes never leave a half-rendered YAML behind. Creates
    the parent directory on first write.
    """
    path = _overrides_path(section)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(overrides, f, sort_keys=False,
                       default_flow_style=False, allow_unicode=True)
    tmp.replace(path)


def apply_overrides(
    assets: list[dict], overrides: dict,
) -> tuple[list[dict], float]:
    """Apply overrides to an asset list. Returns (assets, gap_seconds).

    - manual_sequence: reorders assets by ID. IDs in the sequence that
      don't match any asset are silently skipped. Assets not in the
      sequence are appended at the end in their original order — this
      is intentional defensive behavior so a stale sequence missing a
      newly-promoted render doesn't make that render disappear from
      the player.
    - per_asset_duration_seconds: stamps assets[i]['override_duration_seconds']
      when an override exists for that asset's id. Player consumers should
      prefer this over any other duration source.
    - inter_paragraph_gap_seconds: returned alongside the assets list.
      Falls back to DEFAULT_INTER_PARAGRAPH_GAP_SECONDS when unset.
    """
    seq = overrides.get("manual_sequence") or []
    duration_overrides = overrides.get("per_asset_duration_seconds") or {}
    gap = overrides.get("inter_paragraph_gap_seconds")
    if gap is None:
        gap = DEFAULT_INTER_PARAGRAPH_GAP_SECONDS

    if seq:
        by_id = {a["id"]: a for a in assets}
        ordered: list[dict] = []
        seen_ids: set = set()
        for asset_id in seq:
            asset = by_id.get(asset_id)
            if asset is None or asset_id in seen_ids:
                continue
            ordered.append(asset)
            seen_ids.add(asset_id)
        # Append leftover assets (not in sequence) preserving original order.
        for asset in assets:
            if asset["id"] not in seen_ids:
                ordered.append(asset)
        assets = ordered

    if duration_overrides:
        for asset in assets:
            override = duration_overrides.get(asset["id"])
            if override is not None:
                asset["override_duration_seconds"] = float(override)

    return assets, float(gap)
