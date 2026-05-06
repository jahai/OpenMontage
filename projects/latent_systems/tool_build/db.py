"""Centralized state.db connection helper.

Every connection opened against state.db must apply the Section 7
multi-Claude state coordination PRAGMAs:
  - synchronous=FULL: per-connection setting; not persistent. Forces
    immediate flush so external readers see committed state.
  - foreign_keys=ON: per-connection setting; not persistent. Enforces
    declared FKs (sqlite3 default is OFF).

journal_mode=WAL is set persistently in migration 0001_initial and
written to the database header; it does not need re-setting per
connection.

Anywhere in tool_build/ that opens state.db should use db.connect()
rather than calling sqlite3.connect() directly. Walker, server,
query helpers, ad-hoc analysis scripts — all route through here.

Also runs setup_console_encoding() at import time. Every entry point
in tool_build/ ultimately imports db (directly or via dispatcher), so
piggybacking the UTF-8 stream reconfigure here guarantees standalone
test scripts and ad-hoc invocations get it without duplicating the
serve.py bootstrap. Pattern from AUDIT_PATTERNS.md (Unicode-in-print).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

TOOL_BUILD_DIR = Path(__file__).resolve().parent
DATA_DIR = TOOL_BUILD_DIR / "_data"
DB_PATH = DATA_DIR / "state.db"


def setup_console_encoding() -> None:
    """Force stdout/stderr to UTF-8 so non-ASCII characters in print
    statements (em-dashes, arrows, etc.) don't crash on Windows cp1252.
    Idempotent; safe to call multiple times."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


setup_console_encoding()


def connect(*, require_existing: bool = True) -> sqlite3.Connection:
    """Open state.db with Section 7 PRAGMAs applied.

    If require_existing=True (default), raises FileNotFoundError when
    state.db is missing — the caller likely needs to run
    --migrate-schema first. Set False for the one place that creates
    the database (Alembic env.py + migration tooling).
    """
    if require_existing and not DB_PATH.exists():
        raise FileNotFoundError(
            f"state.db missing at {DB_PATH}; run --migrate-schema first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def journal_mode(conn: sqlite3.Connection) -> str:
    """Return current journal_mode as lowercase string ('wal', 'delete', etc.)."""
    return conn.execute("PRAGMA journal_mode").fetchone()[0].lower()


# FK-respecting deletion order. Children rows that reference parents must
# be deleted FIRST, otherwise foreign_keys=ON raises IntegrityError. Order
# derived from migration 0001 schema:
#   concepts <- prompts <- generation_attempts <- renders <- (verdicts,
#                                                            hero_promotions,
#                                                            lineage_edges)
#                       \- api_calls (FK to prompts)
# Tables without FKs (cross_ai_captures, tool_grammar_configs, app_meta)
# are excluded — tests that touch them clean up directly.
_CASCADE_DELETE_ORDER = (
    # children of renders
    ("verdicts",         "id LIKE ?"),
    ("hero_promotions",  "id LIKE ?"),
    # lineage_edges has no FK but references render IDs through
    # source_id/target_id; clean both sides so test_acceptance-style
    # graph cleanups don't leave dangling edges
    ("lineage_edges",    "id LIKE ? OR source_id LIKE ? OR target_id LIKE ?"),
    # children of prompts
    ("api_calls",        "id LIKE ?"),
    # render itself (FK to prompts AND generation_attempts)
    ("renders",          "id LIKE ?"),
    # generation_attempts FK to prompts
    ("generation_attempts", "id LIKE ?"),
    # prompts FK to concepts
    ("prompts",          "id LIKE ?"),
    # root
    ("concepts",         "id LIKE ?"),
)


def cascading_delete(prefix: str) -> dict[str, int]:
    """Delete every row whose `id` starts with `prefix` from the artifact
    tables, walking the FK graph child-first so foreign_keys=ON does not
    abort the cleanup.

    Tests historically open-coded an 8-line FK-ordered DELETE block
    (Day 5-9 review §5 bug 7). Centralizing here means:
      - one place to update when a new table joins the graph,
      - tests that forget a child table no longer leak rows that fail FK
        on the next run,
      - prefix style (`test_d12_`, `test_acceptance_`) stays a per-test
        decision; this helper just respects whatever pattern the test
        chose for its IDs.

    `lineage_edges` is special-cased: source_id and target_id can carry
    test-prefixed values even when the edge's own id is not test-prefixed
    (e.g. acceptance test seeds reference real renders). The query OR-s
    all three columns so dangling edges are caught.

    Returns a {table: rows_deleted} dict for assertion / debugging.

    Caller's responsibility: deleting concept-rooted rows where the
    children IDs do NOT share the parent's prefix (e.g. test_concept_crud
    keys concepts by name not id) — those tests still need their own
    cleanup logic since the prefix-on-id contract doesn't apply.
    """
    if not prefix or "'" in prefix or "%" in prefix:
        raise ValueError(f"invalid cascade prefix: {prefix!r}")
    pattern = f"{prefix}%"
    counts: dict[str, int] = {}
    conn = connect()
    try:
        with conn:
            for table, where in _CASCADE_DELETE_ORDER:
                placeholders = where.count("?")
                params = (pattern,) * placeholders
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE {where}", params
                )
                counts[table] = cur.rowcount
    finally:
        conn.close()
    return counts
