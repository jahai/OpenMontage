"""audit consultation schema (Phase 2 Wave A prerequisite)

Phase 2 Migration 0003 per phase2_design_notes.md v0.4 §2.

Restructures verdicts via temp-table-and-copy (SQLite ALTER TABLE
can't add FK to existing tables); creates audit_sessions,
ai_consultations, audit_thumbnails. ai_consultations replaces v0.1's
JSON-on-verdicts approach (split per cross-Claude review v0.2 +
Joseph's Q2 call to include supersedes_verdict_id now).

Schema additions:
  - verdicts: + rubric_version, + audit_session_id (FK),
              + consultation_cost_usd, + flags_needs_second_look,
              + supersedes_verdict_id (self-FK)
  - audit_sessions (new): scope tracking + rubric/discipline version +
              cost rollups + mode (quick_pass | deep_eval)
  - ai_consultations (new): per-consultation records linked to
              verdicts via FK; provider, model, status, cost, raw
              response, parsed JSON, failure reason
  - audit_thumbnails (new): hash-stable thumbnail cache per design
              notes §5 thumbnail-serve invalidation logic

Bumps app_meta.schema_version 0002 -> 0003.

Verdicts table is empty at migration time (Phase 2 Wave A hasn't
shipped verdict capture yet), so the temp-table-and-copy moves zero
rows; data preservation concern is structural only. State.db backup
saved at _data/state.db.pre_0003_backup before running.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-06
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: audit_sessions FIRST — verdicts_new will FK to it.
    op.execute("""
        CREATE TABLE audit_sessions (
            id TEXT PRIMARY KEY,
            started TEXT NOT NULL,
            ended TEXT,
            rubric_version TEXT NOT NULL,
            discipline_version TEXT NOT NULL,
            mode TEXT DEFAULT 'quick_pass',
            scope_concept_id TEXT,
            scope_section TEXT,
            scope_filter_json TEXT,
            total_consultations INTEGER DEFAULT 0,
            total_cost_usd REAL DEFAULT 0,
            notes TEXT
        )
    """)
    op.execute("CREATE INDEX idx_audit_sessions_started ON audit_sessions(started)")
    op.execute("CREATE INDEX idx_audit_sessions_rubric ON audit_sessions(rubric_version)")
    op.execute(
        "CREATE INDEX idx_audit_sessions_concept ON audit_sessions(scope_concept_id) "
        "WHERE scope_concept_id IS NOT NULL"
    )

    # Step 2: rebuild verdicts via temp-table-and-copy.
    # SQLite ALTER TABLE can't add FK to existing tables. Empty verdicts
    # at migration time so copy is structural only.
    op.execute("""
        CREATE TABLE verdicts_new (
            id TEXT PRIMARY KEY,
            render_id TEXT NOT NULL,
            rubric_used TEXT,
            rubric_version TEXT,
            verdict TEXT NOT NULL,
            audited_by TEXT,
            audit_session_id TEXT,
            consultation_cost_usd REAL DEFAULT 0,
            flags_needs_second_look INTEGER DEFAULT 0,
            supersedes_verdict_id TEXT,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY(render_id) REFERENCES renders(id),
            FOREIGN KEY(audit_session_id) REFERENCES audit_sessions(id),
            FOREIGN KEY(supersedes_verdict_id) REFERENCES verdicts(id)
        )
    """)
    # Copy preserved columns from old verdicts; new columns get defaults.
    op.execute("""
        INSERT INTO verdicts_new
            (id, render_id, rubric_used, verdict, audited_by,
             discipline_version, yaml_path, created)
        SELECT id, render_id, rubric_used, verdict, audited_by,
               discipline_version, yaml_path, created
        FROM verdicts
    """)
    # Drop old indexes explicitly before dropping table (some SQLite
    # versions auto-drop indexes with the table; doing it explicitly is
    # a no-op on success and a clean error path otherwise).
    op.execute("DROP INDEX IF EXISTS idx_verdicts_render_id")
    op.execute("DROP INDEX IF EXISTS idx_verdicts_verdict")
    op.execute("DROP TABLE verdicts")
    op.execute("ALTER TABLE verdicts_new RENAME TO verdicts")
    # Recreate base indexes + add new ones for v0.3 schema fields.
    op.execute("CREATE INDEX idx_verdicts_render_id ON verdicts(render_id)")
    op.execute("CREATE INDEX idx_verdicts_verdict ON verdicts(verdict)")
    op.execute(
        "CREATE INDEX idx_verdicts_audit_session ON verdicts(audit_session_id) "
        "WHERE audit_session_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX idx_verdicts_flags ON verdicts(flags_needs_second_look) "
        "WHERE flags_needs_second_look = 1"
    )
    op.execute(
        "CREATE INDEX idx_verdicts_supersedes ON verdicts(supersedes_verdict_id) "
        "WHERE supersedes_verdict_id IS NOT NULL"
    )

    # Step 3: ai_consultations (FK to verdicts; verdicts now exists with
    # new schema). Replaces v0.1 design's JSON column on verdicts per
    # cross-Claude review v0.2 — concrete query patterns Phase 2 needs
    # (verdicts-by-provider-failure, cost-rollup-by-provider, all-failed
    # consultations) are awkward and slow against JSON-in-SQLite.
    op.execute("""
        CREATE TABLE ai_consultations (
            id TEXT PRIMARY KEY,
            verdict_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            consulted_at TEXT NOT NULL,
            status TEXT NOT NULL,
            cost_usd REAL DEFAULT 0,
            used_downscale INTEGER DEFAULT 0,
            raw_response TEXT,
            parsed_json TEXT,
            failure_reason TEXT,
            yaml_path TEXT,
            FOREIGN KEY(verdict_id) REFERENCES verdicts(id)
        )
    """)
    op.execute("CREATE INDEX idx_ai_consultations_verdict_id ON ai_consultations(verdict_id)")
    op.execute("CREATE INDEX idx_ai_consultations_provider ON ai_consultations(provider)")
    op.execute("CREATE INDEX idx_ai_consultations_status ON ai_consultations(status)")
    op.execute("CREATE INDEX idx_ai_consultations_consulted_at ON ai_consultations(consulted_at)")

    # Step 4: audit_thumbnails (FK to renders; renders exists from 0001).
    # render_id is PRIMARY KEY → auto-indexed; no additional index needed.
    op.execute("""
        CREATE TABLE audit_thumbnails (
            render_id TEXT PRIMARY KEY,
            thumbnail_path TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            bytes INTEGER NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY(render_id) REFERENCES renders(id)
        )
    """)

    # Step 5: bump app_meta.schema_version per migration boilerplate
    # (Days 5-9 review §3.7 / F5 pattern; see 0002 precedent).
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
        f"VALUES ('schema_version', '0003', '{now}')"
    )


def downgrade() -> None:
    # Drop child tables first (FK to verdicts and renders).
    op.execute("DROP TABLE IF EXISTS audit_thumbnails")
    op.execute("DROP INDEX IF EXISTS idx_ai_consultations_consulted_at")
    op.execute("DROP INDEX IF EXISTS idx_ai_consultations_status")
    op.execute("DROP INDEX IF EXISTS idx_ai_consultations_provider")
    op.execute("DROP INDEX IF EXISTS idx_ai_consultations_verdict_id")
    op.execute("DROP TABLE IF EXISTS ai_consultations")

    # Rebuild verdicts back to 0002 schema (temp-table-and-copy reverse).
    op.execute("""
        CREATE TABLE verdicts_old (
            id TEXT PRIMARY KEY,
            render_id TEXT NOT NULL,
            rubric_used TEXT,
            verdict TEXT NOT NULL,
            audited_by TEXT,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY(render_id) REFERENCES renders(id)
        )
    """)
    op.execute("""
        INSERT INTO verdicts_old
            (id, render_id, rubric_used, verdict, audited_by,
             discipline_version, yaml_path, created)
        SELECT id, render_id, rubric_used, verdict, audited_by,
               discipline_version, yaml_path, created
        FROM verdicts
    """)
    op.execute("DROP INDEX IF EXISTS idx_verdicts_supersedes")
    op.execute("DROP INDEX IF EXISTS idx_verdicts_flags")
    op.execute("DROP INDEX IF EXISTS idx_verdicts_audit_session")
    op.execute("DROP INDEX IF EXISTS idx_verdicts_verdict")
    op.execute("DROP INDEX IF EXISTS idx_verdicts_render_id")
    op.execute("DROP TABLE verdicts")
    op.execute("ALTER TABLE verdicts_old RENAME TO verdicts")
    op.execute("CREATE INDEX idx_verdicts_render_id ON verdicts(render_id)")
    op.execute("CREATE INDEX idx_verdicts_verdict ON verdicts(verdict)")

    # Drop audit_sessions LAST — verdicts no longer FKs to it now that
    # the rebuild is back to 0002 schema.
    op.execute("DROP INDEX IF EXISTS idx_audit_sessions_concept")
    op.execute("DROP INDEX IF EXISTS idx_audit_sessions_rubric")
    op.execute("DROP INDEX IF EXISTS idx_audit_sessions_started")
    op.execute("DROP TABLE IF EXISTS audit_sessions")

    # Restore app_meta.schema_version to 0002.
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
        f"VALUES ('schema_version', '0002', '{now}')"
    )
