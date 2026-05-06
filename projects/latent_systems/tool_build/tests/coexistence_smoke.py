#!/usr/bin/env python3
"""
Coexistence smoke test — verifies AD-5 promise that v1 does not write to
canonical paths during a Phase 1 user-flow.

Contract (per phase1_design_notes.md Section 4):
    1. Capture pre-test snapshot of canonical paths.
    2. Run a Phase 1 user-flow.
    3. Capture post-test snapshot.
    4. Result must equal baseline, OR show only legitimate router writes.
       "Legitimate" = any destination declared in tools/router_config.yaml.
       (Section 4 step 4 names run_<date>/ as one example; the full
       allowlist is read from router_config so the smoke test stays in
       sync with router behavior automatically.)

Exit 0 on pass; exit 1 on regression (v1-attributable canonical writes).

CANONICAL paths (read-only to v1 per AD-5):
    projects/latent_systems/shared/**
    projects/latent_systems/ep1/**
    projects/latent_systems/docs/**
    projects/latent_systems/tools/**

Phase 1 build sequence (Section 8) — flow stubs to be filled in:
    Week 2 — clipboard handoff + filesystem watcher (3b user-flow)
    Week 3 — API integration + prompt drafting (3a user-flow)
    Week 4 — frontend + concept browser + discipline-drift query

Until those land, run_user_flow() is a no-op and the test verifies the
harness itself: empty flow against clean baseline must produce zero delta.

Usage:
    python tool_build/tests/coexistence_smoke.py
    python tool_build/tests/coexistence_smoke.py --verbose
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Pattern #3 (AUDIT_PATTERNS.md): import db so its module-load
# setup_console_encoding() runs before any print on cp1252 hosts.
# This file doesn't use db functionality; the import is purely
# for the codec side effect.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db  # noqa: E402, F401

CANONICAL_ROOTS = (
    "projects/latent_systems/shared",
    "projects/latent_systems/ep1",
    "projects/latent_systems/docs",
    "projects/latent_systems/tools",
)

ROUTER_CONFIG = "projects/latent_systems/tools/router_config.yaml"

# Fallback allowlist used when router_config.yaml can't be parsed (PyYAML
# not installed, file missing, or malformed). Matches the date-stamped
# run_<YYYY-MM-DD>/ subdir pattern Section 4 step 4 names by example.
FALLBACK_ROUTER_ALLOWLIST = (
    re.compile(r"^projects/latent_systems/shared/[^/]+/run_\d{4}-\d{2}-\d{2}/"),
)


@dataclass(frozen=True)
class StatusEntry:
    status: str
    path: str

    def __str__(self) -> str:
        return f"{self.status} {self.path}"


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(out.stdout.strip())


def load_router_allowlist(verbose: bool = False) -> tuple[re.Pattern[str], ...]:
    """Build the router-legitimate-path allowlist from router_config.yaml.

    The router writes to the destinations declared in router_config (e.g.
    shared/render_craft_exemplars/, shared/visual_identity_phase1_references/,
    ep1/_work/.../_DEPRECATED_*/, docs/). Hardcoding only the run_<date>
    pattern would false-positive REGRESSION on legitimate router writes
    to those other destinations.

    Returns FALLBACK_ROUTER_ALLOWLIST if PyYAML isn't installed or the
    config can't be parsed. Always includes the run_<date> pattern in
    addition to destination-derived patterns.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        if verbose:
            print("[smoke] PyYAML not installed; using fallback allowlist (run_<date>/ only)")
        return FALLBACK_ROUTER_ALLOWLIST

    config_path = repo_root() / ROUTER_CONFIG
    if not config_path.exists():
        if verbose:
            print(f"[smoke] {ROUTER_CONFIG} missing; using fallback allowlist")
        return FALLBACK_ROUTER_ALLOWLIST

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        destinations = config.get("destinations", {}) or {}
    except (yaml.YAMLError, OSError, AttributeError) as e:
        if verbose:
            print(f"[smoke] {ROUTER_CONFIG} unparseable ({e}); using fallback allowlist")
        return FALLBACK_ROUTER_ALLOWLIST

    patterns: list[re.Pattern[str]] = list(FALLBACK_ROUTER_ALLOWLIST)
    for _name, dest in destinations.items():
        if not isinstance(dest, str) or not dest:
            continue
        # Destinations are project-root-relative under projects/latent_systems/.
        # Normalize and escape for regex.
        prefix = f"projects/latent_systems/{dest.strip('/')}/"
        patterns.append(re.compile("^" + re.escape(prefix)))
    return tuple(patterns)


def capture_snapshot(roots: tuple[str, ...] = CANONICAL_ROOTS) -> set[StatusEntry]:
    """Snapshot of canonical paths via `git status --porcelain`.

    Includes modifications, additions, deletions, untracked files. Anything
    appearing here represents working-tree-vs-HEAD divergence inside the
    canonical structure.

    Snapshot semantics: porcelain v1 captures both index-vs-HEAD and
    worktree-vs-HEAD changes. If the hook ever evolves to inspect index
    only (or worktree only), sync this test mechanism accordingly.
    """
    cmd = ["git", "status", "--porcelain", "--", *roots]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=repo_root())
    entries: set[StatusEntry] = set()
    for line in out.stdout.splitlines():
        if not line:
            continue
        # Porcelain v1: XY <space> path  (X = index, Y = worktree)
        status = line[:2]
        path = line[3:]
        # Strip rename "old -> new" → keep new path only (rename target
        # is what landed on disk).
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        # Strip surrounding quotes git emits for paths with special chars.
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        entries.add(StatusEntry(status=status, path=path))
    return entries


def filter_router_legitimate(
    entries: set[StatusEntry],
    allowlist: tuple[re.Pattern[str], ...],
) -> tuple[set[StatusEntry], set[StatusEntry]]:
    """Split entries into (v1_attributable, router_legitimate)."""
    legit, attributable = set(), set()
    for e in entries:
        if any(p.match(e.path) for p in allowlist):
            legit.add(e)
        else:
            attributable.add(e)
    return attributable, legit


def run_user_flow(verbose: bool = False) -> None:
    """Phase 1 user-flow stub. Filled in across Weeks 2-4 per Section 8.

    Today: no-op. Verifies harness against clean baseline.
    """
    # WEEK 2 — clipboard handoff + filesystem watcher (Feature 3b):
    #   - simulate concept create
    #   - simulate prompt draft + lock
    #   - simulate clipboard copy event (no actual paste)
    #   - simulate file landing in ~/Downloads/
    #   - run router; verify it writes to shared/<dir>/run_<date>/ only
    #
    # WEEK 3 — API integration + prompt drafting (Feature 3a):
    #   - mock Anthropic API call
    #   - simulate render capture for API-driven generation
    #   - exercise retry queue path
    #
    # WEEK 4 — frontend + discipline-drift query (Features 1, 9):
    #   - exercise concept browser query path
    #   - exercise discipline-drift query path
    #   - confirm read-only across canonical_roots
    if verbose:
        print("[smoke] run_user_flow: no-op stub (Week 2/3/4 fill-in pending)")


def diff_snapshots(before: set[StatusEntry], after: set[StatusEntry]) -> set[StatusEntry]:
    """Entries present after the flow that were not in the baseline."""
    return after - before


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="print snapshot details")
    args = parser.parse_args()

    try:
        root = repo_root()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: not inside a git repository (or `git` not on PATH).", file=sys.stderr)
        print("Run from within OpenMontage/ or one of its subdirectories.", file=sys.stderr)
        return 2

    if args.verbose:
        print(f"[smoke] repo root: {root}")
        print(f"[smoke] canonical roots: {CANONICAL_ROOTS}")

    allowlist = load_router_allowlist(verbose=args.verbose)
    if args.verbose:
        print(f"[smoke] router allowlist patterns: {len(allowlist)}")
        for p in allowlist:
            print(f"  allow: {p.pattern}")

    before = capture_snapshot()
    if args.verbose:
        print(f"[smoke] baseline entries: {len(before)}")
        for e in sorted(before, key=lambda x: x.path):
            print(f"  baseline: {e}")

    run_user_flow(verbose=args.verbose)

    after = capture_snapshot()
    if args.verbose:
        print(f"[smoke] post-flow entries: {len(after)}")

    new_entries = diff_snapshots(before, after)
    attributable, legit = filter_router_legitimate(new_entries, allowlist)

    if args.verbose and legit:
        print(f"[smoke] router-legitimate writes (allowed): {len(legit)}")
        for e in sorted(legit, key=lambda x: x.path):
            print(f"  router-ok: {e}")

    if attributable:
        print("FAIL: v1-attributable changes to canonical paths detected.", file=sys.stderr)
        for e in sorted(attributable, key=lambda x: x.path):
            print(f"  REGRESSION: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Per AD-5, v1 must not write to projects/latent_systems/{shared,ep1,docs,tools}/.", file=sys.stderr)
        print("Move new writes to projects/latent_systems/tool_build/_data/ or sidecars.", file=sys.stderr)
        return 1

    print(f"PASS: no v1-attributable canonical writes (router-legitimate: {len(legit)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
