"""started_orig column + hero_promotions UNIQUE index

Bundles two banked items into one migration:
  - Day 5-9 review §4.7: add started_orig to generation_attempts so
    kick_attempt can mutate started without losing the original
    dispatch timestamp. Backfill existing rows; auto-populate via
    trigger on future INSERTs that don't set it explicitly.
  - Day 3 review F4: replace the non-unique idx_hero_promotions_render_id
    with a UNIQUE INDEX. Walker is the only inserter today; the
    invariant (one promotion per render) becomes structurally enforced.

Bumps app_meta.schema_version from '0001' to '0002' per the migration
boilerplate in script.py.mako (Days 5-9 review §3.7 / F5).

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-04
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add started_orig column (nullable initially so existing rows aren't
    #    rejected; trigger + backfill ensure it's always populated going forward).
    op.execute(
        "ALTER TABLE generation_attempts ADD COLUMN started_orig TEXT"
    )

    # 2. Backfill existing rows: started_orig = started for all records that
    #    were inserted before this migration. Idempotent (won't overwrite
    #    rows where started_orig is already set).
    op.execute(
        "UPDATE generation_attempts SET started_orig = started "
        "WHERE started_orig IS NULL"
    )

    # 3. Trigger: any INSERT that doesn't explicitly set started_orig gets it
    #    auto-populated from started. Belt-and-suspenders so test fixtures +
    #    forgotten code paths can't leave the field NULL.
    op.execute("""
        CREATE TRIGGER tr_attempts_set_started_orig
        AFTER INSERT ON generation_attempts
        WHEN NEW.started_orig IS NULL
        BEGIN
            UPDATE generation_attempts
            SET started_orig = NEW.started
            WHERE id = NEW.id;
        END
    """)

    # 4. hero_promotions.render_id UNIQUE — drop existing non-unique index,
    #    recreate as UNIQUE. Walker is the only inserter today; existing data
    #    has 3 rows all with distinct render_ids, so no conflicts.
    op.execute("DROP INDEX IF EXISTS idx_hero_promotions_render_id")
    op.execute(
        "CREATE UNIQUE INDEX idx_hero_promotions_render_id "
        "ON hero_promotions(render_id)"
    )

    # 5. Bump app_meta.schema_version per the boilerplate in script.py.mako.
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
        f"VALUES ('schema_version', '0002', '{now}')"
    )


def downgrade() -> None:
    # Restore non-unique index.
    op.execute("DROP INDEX IF EXISTS idx_hero_promotions_render_id")
    op.execute(
        "CREATE INDEX idx_hero_promotions_render_id "
        "ON hero_promotions(render_id)"
    )

    # Drop trigger.
    op.execute("DROP TRIGGER IF EXISTS tr_attempts_set_started_orig")

    # SQLite doesn't support DROP COLUMN cleanly until 3.35+; modern SQLite
    # is fine, but for portability use the table-rebuild pattern. For this
    # migration's scope we accept that downgrade leaves the column in place
    # (data harmless; column nullable).
    # If true downgrade ever needed: ALTER TABLE generation_attempts DROP COLUMN started_orig
    # (requires SQLite 3.35+; check before relying on this).

    # Restore app_meta.schema_version.
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
        f"VALUES ('schema_version', '0001', '{now}')"
    )
