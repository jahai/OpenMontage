"""Stray-file move executor.

Reads per-file YAMLs at _data/_inbox_review/files/, executes:
  - action='route' → mv source → suggested_destination (mkdir -p parents)
  - action='dedupe' → rm source

Logs every operation to MOVE_LEDGER.md (timestamp, action, src, dest, status).

Safety:
  - Refuses to overwrite an existing destination file (logs CONFLICT, skips).
  - Verifies source still exists before move (logs SOURCE_GONE, skips).
  - Captures exceptions per-file; one failure doesn't abort the batch.

NOT a permanent module — operational tool for one specific routing operation.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).parent
FILES_DIR = SCRIPT_DIR / "files"
LEDGER = SCRIPT_DIR / "MOVE_LEDGER.md"

# Resolve repo root from script location:
# tool_build/_data/_inbox_review/_executor.py → up 4 levels to OpenMontage/
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent.parent


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_destination(suggested: str) -> Path:
    """Resolve a 'projects/latent_systems/...' path to absolute under REPO_ROOT."""
    return REPO_ROOT / suggested


def main() -> int:
    yaml_files = sorted(FILES_DIR.glob("*.yaml"))
    if not yaml_files:
        print(f"No YAML records found at {FILES_DIR}", file=sys.stderr)
        return 1

    rows = []
    summary = {"route_ok": 0, "route_conflict": 0, "route_source_gone": 0,
               "route_error": 0, "dedupe_ok": 0, "dedupe_source_gone": 0,
               "skipped": 0}
    started = _iso_now()

    for yaml_path in yaml_files:
        record = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        action = record.get("proposed_action")
        src = Path(record.get("current_path"))
        dest_str = record.get("suggested_destination", "")

        if action == "route":
            dest = _resolve_destination(dest_str)
            if not src.exists():
                rows.append((_iso_now(), "route", src, dest, "SOURCE_GONE",
                             "source no longer at original path"))
                summary["route_source_gone"] += 1
                continue
            if dest.exists():
                rows.append((_iso_now(), "route", src, dest, "CONFLICT",
                             "destination already exists; skipped"))
                summary["route_conflict"] += 1
                continue
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                rows.append((_iso_now(), "route", src, dest, "OK", ""))
                summary["route_ok"] += 1
            except Exception as e:
                rows.append((_iso_now(), "route", src, dest, "ERROR", str(e)))
                summary["route_error"] += 1

        elif action == "dedupe":
            if not src.exists():
                rows.append((_iso_now(), "dedupe", src, None, "SOURCE_GONE",
                             "source no longer at original path"))
                summary["dedupe_source_gone"] += 1
                continue
            try:
                src.unlink()
                rows.append((_iso_now(), "dedupe", src, None, "OK",
                             "deleted byte-identical browser duplicate"))
                summary["dedupe_ok"] += 1
            except Exception as e:
                rows.append((_iso_now(), "dedupe", src, None, "ERROR", str(e)))
                summary["route_error"] += 1

        else:
            rows.append((_iso_now(), "skip", src, None, "SKIPPED",
                         f"action={action} (not route/dedupe)"))
            summary["skipped"] += 1

    finished = _iso_now()

    # Write ledger
    md = []
    md.append("# Stray-file Move Ledger")
    md.append("")
    md.append(f"**Started:** {started}")
    md.append(f"**Finished:** {finished}")
    md.append(f"**Total records processed:** {len(yaml_files)}")
    md.append("")
    md.append("## Summary")
    md.append("")
    md.append("| Outcome | Count |")
    md.append("|---|---:|")
    for k, v in summary.items():
        if v:
            md.append(f"| {k} | {v} |")
    md.append("")
    md.append("## Operations")
    md.append("")
    md.append("| Timestamp | Action | Source | Destination | Status | Notes |")
    md.append("|---|---|---|---|---|---|")
    for ts, action, src, dest, status, notes in rows:
        src_short = str(src).replace(str(REPO_ROOT), "<REPO>").replace("C:\\Users\\josep\\Downloads\\", "Downloads/")
        dest_short = str(dest).replace(str(REPO_ROOT), "<REPO>") if dest else "—"
        notes_cell = notes.replace("|", "\\|") if notes else ""
        md.append(f"| {ts} | {action} | `{src_short}` | `{dest_short}` | **{status}** | {notes_cell} |")
    md.append("")

    LEDGER.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote ledger: {LEDGER}")
    print()
    print("Summary:")
    for k, v in summary.items():
        if v:
            print(f"  {k:25s} {v}")

    return 0 if summary["route_error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
