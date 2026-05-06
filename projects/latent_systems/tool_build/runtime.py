"""Server runtime for latent_systems tool_build v1.

Glues FastAPI app (app.py) to uvicorn with:
  - PID file management at _data/_server.pid (write on startup, remove on shutdown)
  - Shutdown-file watcher at _data/_server.shutdown (poll-based graceful stop)
  - Schema-version check on startup (refuse to start on mismatch)
  - Logging to _data/_app_log.txt for backgrounded (pythonw) operation

Why control-file shutdown? On Windows, os.kill(pid, signal.SIGTERM) calls
TerminateProcess — hard kill, no cleanup. Filesystem-mediated triggers work
identically on Win/macOS/Linux and survive pythonw (no console for Ctrl+C).
The watcher polls every WATCHER_INTERVAL_S seconds; cmd_stop writes the
file; uvicorn's should_exit flag triggers graceful drain + lifespan
shutdown handlers (PID file removal, log flush).

Phase 1 default: backgrounded via `pythonw tool_build/serve.py`.
Phase 1 debug:  foreground via `python tool_build/serve.py --debug`.
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import uvicorn

import db
import watcher as _watcher_mod
import router_tail as _router_tail_mod
from constants import SUPPORTED_SCHEMA_VERSIONS


WATCHER_INTERVAL_S = 1.0
ROUTER_TAIL_INTERVAL_S = 10.0
RETRY_QUEUE_INTERVAL_S = 30.0
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7890

DATA_DIR = db.DATA_DIR
PID_FILE = DATA_DIR / "_server.pid"
SHUTDOWN_FILE = DATA_DIR / "_server.shutdown"
APP_LOG = DATA_DIR / "_app_log.txt"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    try:
        APP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with APP_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{_iso_now()} [runtime] {msg}\n")
    except OSError:
        pass


def _check_schema() -> None:
    """Raise if schema_version is missing or unsupported.
    Reads SUPPORTED_SCHEMA_VERSIONS from constants — single source of
    truth across migrations (Day 10 / 0002 lift)."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT value FROM app_meta WHERE key='schema_version'"
        ).fetchone()
    if row is None:
        raise RuntimeError("app_meta.schema_version missing; run --migrate-schema first")
    if row[0] not in SUPPORTED_SCHEMA_VERSIONS:
        raise RuntimeError(
            f"unsupported schema_version='{row[0]}' (runtime supports {sorted(SUPPORTED_SCHEMA_VERSIONS)}). "
            f"Run --migrate-schema if behind, or update SUPPORTED_SCHEMA_VERSIONS if ahead."
        )


def _write_pid() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _cleanup_pid() -> None:
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except OSError:
        pass


def _cleanup_shutdown_trigger() -> None:
    try:
        if SHUTDOWN_FILE.exists():
            SHUTDOWN_FILE.unlink()
    except OSError:
        pass


_uvicorn_server_ref: Optional[uvicorn.Server] = None
_download_watcher_ref: Optional[_watcher_mod.DownloadWatcher] = None


def get_download_watcher() -> Optional[_watcher_mod.DownloadWatcher]:
    """Accessor for app.py endpoints. Returns None if not yet started."""
    return _download_watcher_ref


async def _watch_for_shutdown() -> None:
    """Background task: poll for SHUTDOWN_FILE; signal uvicorn to drain when seen."""
    while True:
        if SHUTDOWN_FILE.exists():
            _log(f"shutdown trigger detected at {SHUTDOWN_FILE}; initiating graceful shutdown")
            if _uvicorn_server_ref is not None:
                _uvicorn_server_ref.should_exit = True
            return
        try:
            await asyncio.sleep(WATCHER_INTERVAL_S)
        except asyncio.CancelledError:
            return


_last_router_tail_summary: Optional[dict] = None


def get_last_router_tail_summary() -> Optional[dict]:
    """Accessor for /routing_events endpoint."""
    return _last_router_tail_summary


_last_retry_processor_summary: Optional[dict] = None


def get_last_retry_processor_summary() -> Optional[dict]:
    """Accessor for /retry_queue endpoint."""
    return _last_retry_processor_summary


async def _process_retry_queue() -> None:
    """Background task: scan retry_queue for eligible entries every N
    seconds; execute retry for each via dispatcher.retry_prompt.

    Each retry runs in a thread executor to avoid blocking the event loop
    on a 5-30s API call.
    """
    global _last_retry_processor_summary
    while True:
        try:
            await asyncio.sleep(RETRY_QUEUE_INTERVAL_S)
        except asyncio.CancelledError:
            return
        try:
            import retry_queue
            import dispatcher
            eligible = retry_queue.eligible_for_retry()
            if not eligible:
                _last_retry_processor_summary = {
                    "tick_at": _iso_now(), "eligible": 0, "processed": 0,
                }
                continue
            loop = asyncio.get_running_loop()
            processed = []
            for entry in eligible:
                pid = entry["prompt_id"]
                _log(f"retry-queue: attempting {pid} (attempt {entry['attempts']+1}/{entry['max_attempts']})")
                try:
                    result = await loop.run_in_executor(None, dispatcher.retry_prompt, pid)
                    processed.append({
                        "prompt_id": pid,
                        "ok": result.get("ok", False),
                        "queue_state": result.get("queue_state", "unknown"),
                    })
                    _log(f"retry-queue: {pid} -> {result.get('ok', False)}")
                except Exception as e:
                    _log(f"retry-queue: {pid} crash: {e}")
                    processed.append({"prompt_id": pid, "ok": False, "error": str(e)})
            _last_retry_processor_summary = {
                "tick_at": _iso_now(), "eligible": len(eligible),
                "processed": len(processed), "results": processed,
            }
        except Exception as e:
            _log(f"retry-queue iteration failed: {e}")


async def _tail_router_log() -> None:
    """Background task: periodically ingest new router_log.md content."""
    global _last_router_tail_summary
    # Quick first pass on startup so any pending log content is caught
    # up before the first 10s tick.
    try:
        loop = asyncio.get_running_loop()
        summary = await loop.run_in_executor(None, _router_tail_mod.ingest)
        _last_router_tail_summary = summary
        if summary.get("ingested") or summary.get("errors"):
            _log(f"router-tail startup: {summary}")
    except Exception as e:
        _log(f"router-tail startup failed: {e}")

    while True:
        try:
            await asyncio.sleep(ROUTER_TAIL_INTERVAL_S)
        except asyncio.CancelledError:
            return
        try:
            loop = asyncio.get_running_loop()
            summary = await loop.run_in_executor(None, _router_tail_mod.ingest)
            _last_router_tail_summary = summary
            if summary.get("ingested"):
                _log(f"router-tail: ingested {summary['ingested']} events")
            if summary.get("errors"):
                _log(f"router-tail WARN: {summary['errors']} errors")
        except Exception as e:
            _log(f"router-tail iteration failed: {e}")


@asynccontextmanager
async def _lifespan(app):
    # Startup: clean any stale shutdown trigger from prior crash, write PID,
    # start downloads watcher, start shutdown-trigger watcher.
    global _download_watcher_ref
    _cleanup_shutdown_trigger()
    _check_schema()
    _write_pid()
    _log(f"startup: PID={os.getpid()} port={DEFAULT_PORT}")

    # Downloads watcher: hashes new files in ~/Downloads/ for 3b.7
    # rename-stable identity. Reconcile first to catch anything that
    # appeared while the server was down.
    try:
        dl_watcher = _watcher_mod.DownloadWatcher()
        reconcile_summary = dl_watcher.reconcile()
        _log(f"watcher reconcile: {reconcile_summary}")
        dl_watcher.start()
        _download_watcher_ref = dl_watcher
        _log(f"watcher started: {dl_watcher.downloads_path}")
    except Exception as e:
        _log(f"watcher startup failed: {e}")
        _download_watcher_ref = None

    shutdown_task = asyncio.create_task(_watch_for_shutdown())
    router_tail_task = asyncio.create_task(_tail_router_log())
    retry_queue_task = asyncio.create_task(_process_retry_queue())
    try:
        yield
    finally:
        shutdown_task.cancel()
        router_tail_task.cancel()
        retry_queue_task.cancel()
        for task in (shutdown_task, router_tail_task, retry_queue_task):
            try:
                await task
            except asyncio.CancelledError:
                pass
        if _download_watcher_ref is not None:
            try:
                _download_watcher_ref.stop()
                _log("watcher stopped")
            except Exception as e:
                _log(f"watcher stop failed: {e}")
            _download_watcher_ref = None
        _log("shutdown: uvicorn drain complete")
        _cleanup_pid()
        _cleanup_shutdown_trigger()


def serve(*, debug: bool = False, port: int = DEFAULT_PORT) -> int:
    """Run the server until shutdown trigger or signal. Returns exit code."""
    from app import app as fastapi_app
    fastapi_app.router.lifespan_context = _lifespan

    log_level = "debug" if debug else "info"
    config = uvicorn.Config(
        fastapi_app,
        host=DEFAULT_HOST,
        port=port,
        log_level=log_level,
        access_log=debug,
        # Disable uvicorn's signal handlers so our control-file mechanism
        # is the only shutdown path. (uvicorn defaults to handling SIGINT/
        # SIGTERM; under pythonw there's no console anyway, but explicit is
        # better than implicit.)
    )
    server = uvicorn.Server(config)
    global _uvicorn_server_ref
    _uvicorn_server_ref = server
    try:
        server.run()
    except KeyboardInterrupt:
        # Foreground/debug Ctrl+C path. Lifespan still runs.
        _log("KeyboardInterrupt received; shutting down")
        return 130
    except Exception as e:
        _log(f"server crash: {e}")
        _cleanup_pid()
        _cleanup_shutdown_trigger()
        print(f"[runtime] FATAL: {e}", file=sys.stderr)
        return 1
    finally:
        _uvicorn_server_ref = None
    return 0
