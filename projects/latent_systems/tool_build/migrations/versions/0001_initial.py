"""initial schema

Creates all 11 tables verbatim per phase1_design_notes.md Section 2:
concepts, prompts, generation_attempts, renders, verdicts,
hero_promotions, lineage_edges, api_calls, cross_ai_captures,
tool_grammar_configs, app_meta. Plus all declared indexes.

Seeds app_meta with schema_version='0001' so future startup checks have
a value to compare against (per Section 6 — server refuses to start if
schema_version mismatch detected without --migrate-schema flag).

Revision ID: 0001
Revises:
Create Date: 2026-05-04
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite-specific: enable WAL + synchronous=FULL per Section 7
    # multi-Claude state coordination constraints (immediate-flush so
    # external readers see committed state without blocking writers).
    op.execute("PRAGMA journal_mode = WAL")
    op.execute("PRAGMA synchronous = FULL")

    op.execute("""
        CREATE TABLE concepts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            ep TEXT,
            section TEXT,
            subject TEXT,
            register TEXT,
            status TEXT NOT NULL,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT NOT NULL,
            created TEXT NOT NULL,
            modified TEXT NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_concepts_status ON concepts(status)")
    op.execute("CREATE INDEX idx_concepts_ep ON concepts(ep)")
    op.execute("CREATE INDEX idx_concepts_section ON concepts(section)")
    op.execute("CREATE INDEX idx_concepts_discipline_version ON concepts(discipline_version)")

    op.execute("""
        CREATE TABLE prompts (
            id TEXT PRIMARY KEY,
            concept_id TEXT,
            tool TEXT NOT NULL,
            text_preview TEXT,
            status TEXT NOT NULL,
            failure_reason TEXT,
            drafted_by TEXT,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY(concept_id) REFERENCES concepts(id)
        )
    """)
    op.execute("CREATE INDEX idx_prompts_concept_id ON prompts(concept_id)")
    op.execute("CREATE INDEX idx_prompts_tool ON prompts(tool)")
    op.execute("CREATE INDEX idx_prompts_status ON prompts(status)")

    op.execute("""
        CREATE TABLE generation_attempts (
            id TEXT PRIMARY KEY,
            prompt_id TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            started TEXT NOT NULL,
            completed TEXT,
            status TEXT NOT NULL,
            trigger_method TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY(prompt_id) REFERENCES prompts(id)
        )
    """)
    op.execute("CREATE INDEX idx_attempts_prompt_id ON generation_attempts(prompt_id)")
    op.execute("CREATE INDEX idx_attempts_status ON generation_attempts(status)")
    op.execute("CREATE UNIQUE INDEX idx_attempts_unique_per_prompt ON generation_attempts(prompt_id, attempt_number)")

    op.execute("""
        CREATE TABLE renders (
            id TEXT PRIMARY KEY,
            attempt_id TEXT,
            prompt_id TEXT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            download_hash TEXT,
            canonical_hash TEXT NOT NULL,
            tool TEXT NOT NULL,
            variant INTEGER,
            hero_status TEXT,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT,
            created TEXT NOT NULL,
            FOREIGN KEY(attempt_id) REFERENCES generation_attempts(id),
            FOREIGN KEY(prompt_id) REFERENCES prompts(id)
        )
    """)
    op.execute("CREATE INDEX idx_renders_attempt_id ON renders(attempt_id)")
    op.execute("CREATE INDEX idx_renders_prompt_id ON renders(prompt_id)")
    op.execute("CREATE INDEX idx_renders_canonical_hash ON renders(canonical_hash)")
    op.execute("CREATE INDEX idx_renders_download_hash ON renders(download_hash)")
    op.execute("CREATE INDEX idx_renders_hero_status ON renders(hero_status)")
    op.execute("CREATE INDEX idx_renders_filepath ON renders(filepath)")

    op.execute("""
        CREATE TABLE verdicts (
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
    op.execute("CREATE INDEX idx_verdicts_render_id ON verdicts(render_id)")
    op.execute("CREATE INDEX idx_verdicts_verdict ON verdicts(verdict)")

    op.execute("""
        CREATE TABLE hero_promotions (
            id TEXT PRIMARY KEY,
            render_id TEXT NOT NULL,
            hero_filepath TEXT NOT NULL,
            reversed_at TEXT,
            reversed_reason TEXT,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY(render_id) REFERENCES renders(id)
        )
    """)
    op.execute("CREATE INDEX idx_hero_promotions_render_id ON hero_promotions(render_id)")

    op.execute("""
        CREATE TABLE lineage_edges (
            id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            layer INTEGER NOT NULL,
            valid_from_version TEXT NOT NULL,
            valid_to_version TEXT,
            stale_reason TEXT,
            created TEXT NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_lineage_source ON lineage_edges(source_type, source_id)")
    op.execute("CREATE INDEX idx_lineage_target ON lineage_edges(target_type, target_id)")
    op.execute("CREATE INDEX idx_lineage_layer ON lineage_edges(layer)")
    op.execute("CREATE INDEX idx_lineage_validity ON lineage_edges(valid_from_version, valid_to_version)")

    op.execute("""
        CREATE TABLE api_calls (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            purpose TEXT NOT NULL,
            prompt_id TEXT,
            started TEXT NOT NULL,
            completed TEXT,
            status TEXT NOT NULL,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd_estimate REAL,
            error TEXT,
            FOREIGN KEY(prompt_id) REFERENCES prompts(id)
        )
    """)
    op.execute("CREATE INDEX idx_api_calls_provider ON api_calls(provider)")
    op.execute("CREATE INDEX idx_api_calls_purpose ON api_calls(purpose)")
    op.execute("CREATE INDEX idx_api_calls_started ON api_calls(started)")
    op.execute("CREATE INDEX idx_api_calls_prompt_id ON api_calls(prompt_id)")

    op.execute("""
        CREATE TABLE cross_ai_captures (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT NOT NULL,
            captured TEXT NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_cross_ai_captures_source ON cross_ai_captures(source)")

    op.execute("""
        CREATE TABLE tool_grammar_configs (
            tool TEXT PRIMARY KEY,
            discipline_version TEXT NOT NULL,
            yaml_path TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated TEXT NOT NULL
        )
    """)

    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT INTO app_meta (key, value, updated) VALUES ('schema_version', '0001', '{now}')"
    )


def downgrade() -> None:
    for table in (
        "app_meta", "tool_grammar_configs", "cross_ai_captures", "api_calls",
        "lineage_edges", "hero_promotions", "verdicts", "renders",
        "generation_attempts", "prompts", "concepts",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
