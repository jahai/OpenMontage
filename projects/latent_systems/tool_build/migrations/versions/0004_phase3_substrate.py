"""phase3 substrate — notes_md_state + cross_ai_captures expansion + hero_promotions F5 columns + audio_assets

Migration 0004 per phase3_design_notes.md v0.2 §"Migration 0004 schema
sketch" + Day 2 of Phase 3 sprint additions (2026-05-14).

Fully additive — no temp-table-and-copy required (Migration 0003's
verdicts rebuild was the only one needing that pattern). Existing rows
in `hero_promotions` (3 in production at migration time) are preserved;
the 4 new columns are nullable and backfill via the app layer as F5
fires against them.

Schema additions:
  - notes_md_state (new): per-section NOTES.md state for F6 NOTES.md
    authorship orchestration. Section PK; concepts join via existing
    `concepts.section` FK relationship.
  - cross_ai_captures: 7 new columns for F7 cross-AI capture expansion
    (relevance_binding_type/_id, original_input_text, expansion_text,
    paired_capture_id, provider, consultation_cost_usd) + 2 indexes.
  - hero_promotions: 4 new columns for F5 atomic action gap closure
    (verdict_id, promoted_at, promoted_by, audit_session_id). All
    nullable so the 3 existing rows survive; F5 enforces non-null on
    new inserts via application logic.
  - audio_assets (new): tracks narration audio files (EP1_section_*_
    para_*_radio_news_host_*.mp3) as first-class artifacts for the
    rough-cut player (Days 4-5 of Phase 3 sprint).

Skipped from v0.2 design:
  - idx_verdicts_flagged — already exists as idx_verdicts_flags from
    Migration 0003.
  - unknown_image_terminal renders.tool enum value — application-
    level only; SQLite TEXT column doesn't constrain.
  - doc_set table — deferred to Phase 3.5 (v0.2 decision).

Bumps app_meta.schema_version 0003 -> 0004.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-14
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: notes_md_state — per-section NOTES.md authorship state.
    # F6 reads `last_authored`/`authored_against_discipline_version` to
    # decide which sections are stale; F5 hero_promote() queues an F6
    # prompt-fire that updates this table post-authoring.
    op.execute("""
        CREATE TABLE notes_md_state (
            section TEXT PRIMARY KEY,
            template_version TEXT NOT NULL,
            authored_against_discipline_version TEXT NOT NULL,
            last_authored TEXT,
            last_modified_filepath TEXT,
            last_authored_by TEXT,
            notes TEXT,
            yaml_path TEXT NOT NULL,
            created TEXT NOT NULL,
            modified TEXT NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX idx_notes_md_state_template_version "
        "ON notes_md_state(template_version)"
    )
    op.execute(
        "CREATE INDEX idx_notes_md_state_authored_against "
        "ON notes_md_state(authored_against_discipline_version)"
    )

    # Step 2: cross_ai_captures expansion — 7 new columns per v0.2 design
    # for F7 capture surface (relevance binding + paired captures + cost
    # rollup + provider).
    op.execute("ALTER TABLE cross_ai_captures ADD COLUMN relevance_binding_type TEXT")
    op.execute("ALTER TABLE cross_ai_captures ADD COLUMN relevance_binding_id TEXT")
    op.execute("ALTER TABLE cross_ai_captures ADD COLUMN original_input_text TEXT")
    op.execute("ALTER TABLE cross_ai_captures ADD COLUMN expansion_text TEXT")
    op.execute("ALTER TABLE cross_ai_captures ADD COLUMN paired_capture_id TEXT")
    op.execute("ALTER TABLE cross_ai_captures ADD COLUMN provider TEXT")
    op.execute(
        "ALTER TABLE cross_ai_captures ADD COLUMN consultation_cost_usd "
        "REAL DEFAULT 0"
    )
    op.execute(
        "CREATE INDEX idx_cross_ai_captures_relevance "
        "ON cross_ai_captures(relevance_binding_type, relevance_binding_id)"
    )
    op.execute(
        "CREATE INDEX idx_cross_ai_captures_paired "
        "ON cross_ai_captures(paired_capture_id) "
        "WHERE paired_capture_id IS NOT NULL"
    )

    # Step 3: hero_promotions F5 gap closure — 4 nullable columns the
    # F5_MODAL_UX_DRAFT.md atomic-transaction Python shape names but
    # weren't in the v0.2 schema sketch. Nullable so the 3 existing
    # production rows survive without backfill; F5 enforces non-null
    # at application layer for new inserts.
    op.execute("ALTER TABLE hero_promotions ADD COLUMN verdict_id TEXT")
    op.execute("ALTER TABLE hero_promotions ADD COLUMN promoted_at TEXT")
    op.execute("ALTER TABLE hero_promotions ADD COLUMN promoted_by TEXT")
    op.execute("ALTER TABLE hero_promotions ADD COLUMN audit_session_id TEXT")
    op.execute(
        "CREATE INDEX idx_hero_promotions_verdict_id "
        "ON hero_promotions(verdict_id) "
        "WHERE verdict_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX idx_hero_promotions_audit_session "
        "ON hero_promotions(audit_session_id) "
        "WHERE audit_session_id IS NOT NULL"
    )

    # Step 4: audio_assets — first-class tracking for narration audio
    # files. Schema captures section + paragraph order (drives rough-cut
    # player timeline sequence), variant_label (X-value + period_hack +
    # take), voice_profile (radio_news_host etc.), and is_canonical flag
    # (which variant the rough-cut player plays for this section/para).
    #
    # Filename schema (per project_latent_systems memory v1.4 §13):
    #   EP1_section_<N>_para_<P>_<voice_profile>_X<value>[_periodhack]_take<N>.mp3
    # Walker enumeration parses this filename into the columns below.
    op.execute("""
        CREATE TABLE audio_assets (
            id TEXT PRIMARY KEY,
            filepath TEXT NOT NULL,
            filename TEXT NOT NULL,
            section_label TEXT NOT NULL,
            paragraph_number INTEGER,
            variant_label TEXT,
            voice_profile TEXT NOT NULL,
            discipline_version TEXT NOT NULL,
            duration_seconds REAL,
            canonical_hash TEXT,
            is_canonical INTEGER DEFAULT 0,
            yaml_path TEXT NOT NULL,
            created TEXT NOT NULL,
            modified TEXT NOT NULL
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX idx_audio_assets_filepath "
        "ON audio_assets(filepath)"
    )
    op.execute(
        "CREATE INDEX idx_audio_assets_section_para "
        "ON audio_assets(section_label, paragraph_number)"
    )
    # Canonical-only partial index — rough-cut player's most common query
    # is "give me the canonical variant for each (section, para)".
    op.execute(
        "CREATE INDEX idx_audio_assets_canonical "
        "ON audio_assets(section_label, paragraph_number) "
        "WHERE is_canonical = 1"
    )

    # Step 5: bump app_meta.schema_version per migration boilerplate.
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
        f"VALUES ('schema_version', '0004', '{now}')"
    )


def downgrade() -> None:
    # Drop audio_assets indexes + table.
    op.execute("DROP INDEX IF EXISTS idx_audio_assets_canonical")
    op.execute("DROP INDEX IF EXISTS idx_audio_assets_section_para")
    op.execute("DROP INDEX IF EXISTS idx_audio_assets_filepath")
    op.execute("DROP TABLE IF EXISTS audio_assets")

    # Drop hero_promotions indexes + columns (SQLite 3.35+ supports
    # ALTER TABLE DROP COLUMN; this project's SQLite via Python 3.14 is
    # well past that threshold).
    op.execute("DROP INDEX IF EXISTS idx_hero_promotions_audit_session")
    op.execute("DROP INDEX IF EXISTS idx_hero_promotions_verdict_id")
    op.execute("ALTER TABLE hero_promotions DROP COLUMN audit_session_id")
    op.execute("ALTER TABLE hero_promotions DROP COLUMN promoted_by")
    op.execute("ALTER TABLE hero_promotions DROP COLUMN promoted_at")
    op.execute("ALTER TABLE hero_promotions DROP COLUMN verdict_id")

    # Drop cross_ai_captures indexes + columns.
    op.execute("DROP INDEX IF EXISTS idx_cross_ai_captures_paired")
    op.execute("DROP INDEX IF EXISTS idx_cross_ai_captures_relevance")
    op.execute("ALTER TABLE cross_ai_captures DROP COLUMN consultation_cost_usd")
    op.execute("ALTER TABLE cross_ai_captures DROP COLUMN provider")
    op.execute("ALTER TABLE cross_ai_captures DROP COLUMN paired_capture_id")
    op.execute("ALTER TABLE cross_ai_captures DROP COLUMN expansion_text")
    op.execute("ALTER TABLE cross_ai_captures DROP COLUMN original_input_text")
    op.execute("ALTER TABLE cross_ai_captures DROP COLUMN relevance_binding_id")
    op.execute("ALTER TABLE cross_ai_captures DROP COLUMN relevance_binding_type")

    # Drop notes_md_state.
    op.execute("DROP INDEX IF EXISTS idx_notes_md_state_authored_against")
    op.execute("DROP INDEX IF EXISTS idx_notes_md_state_template_version")
    op.execute("DROP TABLE IF EXISTS notes_md_state")

    # Restore app_meta.schema_version to 0003.
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
        f"VALUES ('schema_version', '0003', '{now}')"
    )
