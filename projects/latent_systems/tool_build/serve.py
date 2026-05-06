#!/usr/bin/env python3
"""
LATENT SYSTEMS tool_build v1 — server + lifecycle entry point.

Implements the operational lifecycle specified in phase1_design_notes.md
Section 6 + Section 9. Day 1 fully implements hook install/uninstall and
data directory init; remaining commands stub out heavy work landing
Day 2-5 with explicit TODO markers tied to design-notes section refs.

Usage:
    python  tool_build/serve.py --init             # initialize, install hook
    pythonw tool_build/serve.py                    # start server (backgrounded)
    python  tool_build/serve.py --debug            # start server (foreground)
    python  tool_build/serve.py --status           # is server running?
    python  tool_build/serve.py --stop             # graceful shutdown
    python  tool_build/serve.py --migrate-schema   # apply Alembic migrations
    python  tool_build/serve.py --rebuild-cache    # walk filesystem -> state.db
    python  tool_build/serve.py --uninstall        # remove hook, preserve _data
    python  tool_build/serve.py --init --yes       # auto-confirm prompts
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
# Ensure sibling modules (walker, future migration helpers) are importable
# regardless of which cwd serve.py was invoked from.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Force stdout/stderr to UTF-8 (Windows cp1252 default chokes on em-dashes,
# arrows, and non-ASCII in print statements per Day 5-9 review §5).
# db imports trigger setup_console_encoding() at module load.
import db  # noqa: E402,F401

DATA_DIR = SCRIPT_DIR / "_data"
PID_FILE = DATA_DIR / "_server.pid"
APP_LOG = DATA_DIR / "_app_log.txt"
DB_PATH = DATA_DIR / "state.db"
HOOK_TEMPLATE = SCRIPT_DIR / "hook_template.sh"
ALEMBIC_INI = SCRIPT_DIR / "alembic.ini"
ALEMBIC_DIR = SCRIPT_DIR / "migrations"
DEFAULT_PORT = 7890

# Marker line present in our hook template. Used to recognize a hook as
# "ours" so we never back it up (which would create a recursive-chain
# hazard: chained-to backup contains chaining logic that picks itself).
HOOK_MARKER = b"# Pre-commit hook installed by latent_systems tool_build v1"

ARTIFACT_SUBDIRS = (
    "concepts",
    "prompts",
    "renders",
    "generation_attempts",
    "verdicts",
    "hero_promotions",
    "lineage_edges",
    "cross_ai_captures",
    "tool_grammar_configs",
)

GITIGNORE_CONTENT = """\
# tool_build runtime files (per phase1_design_notes.md Section 5)
state.db
state.db-wal
state.db-shm
state.db.corrupted_*
_retry_queue.yaml
_app_log.txt*
_api_calls.log*
_regen_log.txt
_server.pid
_server.shutdown
"""


# --- helpers --------------------------------------------------------------

def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(out.stdout.strip())


def hook_path() -> Path:
    return repo_root() / ".git" / "hooks" / "pre-commit"


def iso_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def confirm(prompt: str, default: bool = False, auto_yes: bool = False) -> bool:
    if auto_yes:
        return True
    suffix = " [Y/n]" if default else " [y/N]"
    try:
        resp = input(prompt + suffix + " ").strip().lower()
    except EOFError:
        return default
    if not resp:
        return default
    return resp.startswith("y")


def log_event(msg: str) -> None:
    if not DATA_DIR.exists():
        return
    APP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with APP_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{iso_stamp()} {msg}\n")


def is_running() -> tuple[bool, Optional[int]]:
    """Return (alive, pid). Uses psutil.pid_exists for cross-platform
    correctness (handles the Windows PermissionError edge case that
    os.kill(pid, 0) returns false negatives for)."""
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return False, None
    try:
        import psutil
        return psutil.pid_exists(pid), pid
    except ImportError:
        # Fallback if psutil isn't installed yet (e.g., pre-pip-install
        # bootstrap). Less correct on Windows but better than crashing.
        try:
            os.kill(pid, 0)
            return True, pid
        except (ProcessLookupError, OSError):
            return False, pid


# --- hook install/uninstall ----------------------------------------------

def _hook_kind(content: bytes, template: bytes) -> str:
    """Classify an existing hook's content.

    Returns one of: "current" (matches template; idempotent skip),
    "ours_stale" (carries our marker but content drifted; overwrite,
    no backup — backing up our own hook risks recursive chain), or
    "foreign" (genuine third-party hook; back up + chain).
    """
    if content == template:
        return "current"
    if HOOK_MARKER in content:
        return "ours_stale"
    return "foreign"


def install_hook(auto_yes: bool = False) -> bool:
    """Install pre-commit hook per AD-5 v0.5 carve-out. Idempotent.

    Backup-and-chain only fires for foreign hooks. Stale Latent Systems
    hooks are overwritten without backup to keep the chain non-recursive.

    Returns True if installed or already current; False if user declined.
    """
    if not HOOK_TEMPLATE.exists():
        print(f"[init] ERROR: hook template missing at {HOOK_TEMPLATE}", file=sys.stderr)
        return False
    template = HOOK_TEMPLATE.read_bytes()
    hook = hook_path()

    kind = _hook_kind(hook.read_bytes(), template) if hook.exists() else "absent"

    if kind == "current":
        print(f"[init] Hook already installed at {hook} (matches template). Skipping.")
        log_event("hook install skipped: already current")
        return True

    print()
    print(f"Install git pre-commit hook at {hook}?")
    print("This hook enforces AD-5 (canonical paths read-only to non-Joseph commits).")
    print()
    if kind == "absent":
        print("Detected existing hook: none")
        print("If installing: no backup needed (no existing hook present).")
    elif kind == "ours_stale":
        print(f"Detected existing hook: {hook} (Latent Systems hook, content drifted)")
        print("If installing: overwrite with current template. No backup needed")
        print("               (backing up our own hook would create recursive-chain risk).")
    elif kind == "foreign":
        print(f"Detected existing hook: {hook} (foreign — not Latent Systems)")
        print("If installing: existing hook will be backed up to pre-commit.backup_<timestamp>")
        print("               and chained (called first by new hook).")
    print()

    if not confirm("Install?", default=False, auto_yes=auto_yes):
        print("[init] Hook install declined. Build-time write protection reduced;")
        print("       runtime smoke test still operative.")
        log_event("hook install declined by user")
        return False

    if kind == "foreign":
        backup = hook.parent / f"pre-commit.backup_{iso_stamp()}"
        shutil.copy2(hook, backup)
        os.chmod(backup, 0o755)
        print(f"[init] Backed up foreign hook -> {backup.name}")
        log_event(f"hook backup created: {backup.name}")
    elif kind == "ours_stale":
        # No backup: backing up an LS hook would create recursive-chain risk
        # (the new hook chains to most-recent backup_*; if that backup is
        # itself an LS hook, its own chain logic picks the same backup,
        # recursing infinitely). Recovery for prior LS hook revisions is
        # via git history of hook_template.sh, not .git/hooks/ backups.
        print("[init] Overwriting stale Latent Systems hook (no backup).")
        log_event("hook overwritten: stale Latent Systems hook (no backup)")

    hook.write_bytes(template)
    os.chmod(hook, 0o755)
    print(f"[init] Hook installed at {hook}")
    log_event("hook installed")
    return True


def uninstall_hook() -> bool:
    hook = hook_path()
    if not hook.exists():
        print("[uninstall] No pre-commit hook to remove.")
        return True

    content = hook.read_bytes()
    if HOOK_MARKER not in content:
        print(f"[uninstall] Hook at {hook} is not a Latent Systems hook.")
        print("            Refusing to remove third-party hook.")
        return False

    # Restore the most recent FOREIGN backup. Latent Systems backups
    # are skipped — restoring one would re-introduce the same hook
    # we're trying to uninstall.
    backups = sorted(hook.parent.glob("pre-commit.backup_*"), reverse=True)
    foreign_backup = None
    for b in backups:
        try:
            if HOOK_MARKER not in b.read_bytes():
                foreign_backup = b
                break
        except OSError:
            continue

    if foreign_backup is not None:
        shutil.copy2(foreign_backup, hook)
        os.chmod(hook, 0o755)
        print(f"[uninstall] Restored prior foreign hook from {foreign_backup.name}")
        log_event(f"hook uninstalled; restored from {foreign_backup.name}")
    else:
        hook.unlink()
        print(f"[uninstall] Removed hook at {hook} (no foreign backup to restore)")
        log_event("hook uninstalled; no foreign backup to restore")
    return True


# --- _data init -----------------------------------------------------------

def init_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ARTIFACT_SUBDIRS:
        (DATA_DIR / sub).mkdir(exist_ok=True)
    gi = DATA_DIR / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE_CONTENT)
        print(f"[init] Wrote {gi.name}")
    print(f"[init] Data directory ready at {DATA_DIR}")


# --- commands -------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    print("[init] Initializing tool_build v1 ...")
    init_data_dir()

    print("[init] Applying schema migration (alembic upgrade head) ...")
    migrate_rc = _run_alembic_upgrade()
    if migrate_rc != 0:
        print("[init] WARN: migration failed; continuing with remaining init steps.", file=sys.stderr)
        print("[init] WARN: rerun via --migrate-schema once the issue is fixed.", file=sys.stderr)
    else:
        print("[init] Walking canonical paths for pre_v1 render markers ...")
        try:
            from walker import walk as _walk
            summary = _walk(repo_root=repo_root(), dry_run=False, verbose=False)
            print(f"[init] Walker summary: walked={summary['walked']}, "
                  f"new_render={summary['new_render']}, "
                  f"skipped_existing={summary['skipped_existing']}, "
                  f"new_hero={summary['new_hero']}, errors={summary['errors']}")
            log_event(f"walker: {summary}")
        except Exception as e:
            print(f"[init] WARN: walker failed: {e}", file=sys.stderr)
            log_event(f"walker failed: {e}")

    # Week 3 Day 11: load MJ tool-grammar seed (Section 3)
    try:
        import seeds_loader
        seed_summaries = seeds_loader.load_all_seeds()
        for s in seed_summaries:
            print(f"[init] tool-grammar seed: {s['tool']} -> {s['action']}")
    except Exception as e:
        print(f"[init] WARN: seeds_loader failed: {e}", file=sys.stderr)
        log_event(f"seeds_loader failed: {e}")

    install_hook(auto_yes=args.yes)

    print()
    print("[init] Init complete. Server not yet running.")
    print("[init] Start with: pythonw tool_build/serve.py")
    return 0


def _run_alembic_upgrade() -> int:
    """Run `alembic upgrade head` against tool_build/_data/state.db.

    Returns 0 on success, 1 on failure. Caller decides whether to abort
    or continue. Module imports happen inside the function so callers
    that don't need migration (e.g. --status) don't pay import cost.
    """
    try:
        from alembic.config import Config
        from alembic import command
    except ImportError:
        print("[migrate] FAILED: alembic not installed. Run pip install -r requirements.txt.", file=sys.stderr)
        log_event("migrate failed: alembic not installed")
        return 1
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    try:
        command.upgrade(cfg, "head")
    except Exception as e:
        print(f"[migrate] FAILED: {e}", file=sys.stderr)
        log_event(f"migrate failed: {e}")
        return 1
    log_event("migrate: alembic upgrade head completed")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    running, pid = is_running()
    if running:
        print(f"running on port {DEFAULT_PORT} (PID {pid})")
        return 0
    if pid is not None:
        print(f"not running (stale PID file at {PID_FILE} pointed to {pid})")
    else:
        print("not running")
    return 1


def cmd_stop(args: argparse.Namespace) -> int:
    """Graceful stop via filesystem-mediated trigger.

    Writes _data/_server.shutdown; the running server's watcher polls
    for it (1s interval) and signals uvicorn to drain in-flight
    requests, run lifespan shutdown handlers (PID file removal, log
    flush), and exit. Falls back to TerminateProcess after timeout.
    """
    running, pid = is_running()
    if not running:
        if PID_FILE.exists():
            PID_FILE.unlink()
            print("not running (removed stale PID file)")
        else:
            print("not running")
        return 0

    shutdown_file = DATA_DIR / "_server.shutdown"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutdown_file.write_text(iso_stamp())
    print(f"stopping PID {pid} via shutdown trigger ...")
    log_event(f"cmd_stop: shutdown trigger written for PID {pid}")

    # Poll PID file removal — lifespan shutdown handler removes it on
    # graceful exit. Total budget: 15s (more than the 1s watcher poll
    # interval + uvicorn drain time).
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        time.sleep(0.5)
        if not is_running()[0]:
            print("stopped")
            log_event(f"cmd_stop: PID {pid} exited gracefully")
            # Belt-and-suspenders: clean trigger file if server didn't
            # remove it (e.g., crashed mid-shutdown after detecting trigger).
            if shutdown_file.exists():
                try:
                    shutdown_file.unlink()
                except OSError:
                    pass
            return 0

    # Timeout fallback: hard kill via psutil. Log loudly — graceful path
    # failed to drain, which is a real signal worth noticing.
    print("graceful shutdown timed out after 15s; falling back to TerminateProcess",
          file=sys.stderr)
    log_event(f"cmd_stop WARN: graceful timeout for PID {pid}; hard kill")
    try:
        import psutil
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5.0)
    except Exception as e:
        print(f"hard kill failed: {e}", file=sys.stderr)
        return 1
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()
        if shutdown_file.exists():
            shutdown_file.unlink()
    print("stopped (hard kill)")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    print("[uninstall] Stopping server (if running) ...")
    cmd_stop(args)

    print("[uninstall] Removing pre-commit hook ...")
    uninstall_hook()

    if DATA_DIR.exists():
        target = DATA_DIR.parent / f"_data.uninstalled_{iso_stamp()}"
        DATA_DIR.rename(target)
        print(f"[uninstall] Data preserved at {target}")
    else:
        print("[uninstall] No _data/ directory to preserve.")

    print("[uninstall] Uninstall complete.")
    return 0


def cmd_migrate_schema(args: argparse.Namespace) -> int:
    print("[migrate] Running alembic upgrade head ...")
    rc = _run_alembic_upgrade()
    if rc != 0:
        return rc
    print("[migrate] Migration applied.")
    # Verify journal_mode is WAL post-migration. PRAGMA journal_mode = WAL
    # in a migration is sensitive to Alembic's transaction handling; if a
    # future Alembic version changes that handling silently, this check
    # surfaces the regression rather than letting Section 7's multi-Claude
    # coordination guarantee quietly weaken.
    try:
        import db
        with db.connect() as conn:
            mode = db.journal_mode(conn)
            if mode != "wal":
                print(
                    f"[migrate] WARN: journal_mode is '{mode}', expected 'wal'. "
                    f"Section 7 multi-Claude coordination guarantee may be weakened.",
                    file=sys.stderr,
                )
                log_event(f"migrate WARN: journal_mode={mode} not wal")
            else:
                log_event("migrate verified: journal_mode=wal")
    except Exception as e:
        print(f"[migrate] WARN: could not verify journal_mode ({e})", file=sys.stderr)
    return 0


def cmd_rebuild_cache(args: argparse.Namespace) -> int:
    # TODO Day 2-3: walk filesystem, rebuild state.db (Section 2 regen path)
    print("not yet implemented: walk filesystem, rebuild state.db (Section 2 — Day 2-3)", file=sys.stderr)
    return 1


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the FastAPI server.

    If invoked via `python tool_build/serve.py [--debug]`, runs in
    foreground (terminal stays attached; Ctrl+C exits).
    If invoked via `pythonw tool_build/serve.py`, runs detached from
    terminal (Section 6 default — no console window).

    Either way, graceful shutdown is via cmd_stop writing the
    _data/_server.shutdown trigger file.
    """
    running, existing_pid = is_running()
    if running:
        print(f"server already running on port {DEFAULT_PORT} (PID {existing_pid})")
        return 1
    # Stale PID file? Clean it.
    if PID_FILE.exists():
        PID_FILE.unlink()

    if not DB_PATH.exists():
        print(f"state.db missing at {DB_PATH}; run --init or --migrate-schema first.",
              file=sys.stderr)
        return 1

    log_event(f"cmd_serve: starting (debug={args.debug}) on port {DEFAULT_PORT}")
    try:
        import runtime
        return runtime.serve(debug=args.debug, port=DEFAULT_PORT)
    except Exception as e:
        print(f"[serve] FATAL: {e}", file=sys.stderr)
        log_event(f"cmd_serve crash: {e}")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return 1


# --- main -----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--init", action="store_true",
                   help="initialize _data/, run schema migration, walk filesystem, install pre-commit hook")
    g.add_argument("--status", action="store_true", help="report server running/not running")
    g.add_argument("--stop", action="store_true", help="graceful shutdown")
    g.add_argument("--uninstall", action="store_true",
                   help="stop server, remove hook (restore backup), preserve _data/ at _data.uninstalled_<ts>/")
    g.add_argument("--migrate-schema", dest="migrate_schema", action="store_true",
                   help="apply pending Alembic migrations")
    g.add_argument("--rebuild-cache", dest="rebuild_cache", action="store_true",
                   help="rebuild state.db from filesystem source-of-truth")
    g.add_argument("--debug", action="store_true",
                   help="start server in foreground with verbose logging")
    parser.add_argument("--yes", action="store_true",
                        help="auto-confirm interactive prompts (for scripted use)")
    args = parser.parse_args()

    if args.init:
        return cmd_init(args)
    if args.status:
        return cmd_status(args)
    if args.stop:
        return cmd_stop(args)
    if args.uninstall:
        return cmd_uninstall(args)
    if args.migrate_schema:
        return cmd_migrate_schema(args)
    if args.rebuild_cache:
        return cmd_rebuild_cache(args)
    return cmd_serve(args)


if __name__ == "__main__":
    sys.exit(main())
