"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

    # Migrations should keep app_meta.schema_version aligned with Alembic.
    # Walker (and any other schema_version-checking component) reads this
    # value to decide whether to refuse-to-run. Uncomment and replace the
    # version below with this migration's revision id:
    #
    # from datetime import datetime, timezone
    # _now = datetime.now(timezone.utc).isoformat()
    # op.execute(
    #     f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
    #     f"VALUES ('schema_version', '{up_revision}', '{_now}')"
    # )


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}

    # Mirror the schema_version update — set app_meta.schema_version
    # back to this migration's down_revision (the prior version):
    #
    # from datetime import datetime, timezone
    # _now = datetime.now(timezone.utc).isoformat()
    # op.execute(
    #     f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
    #     f"VALUES ('schema_version', '{down_revision}', '{_now}')"
    # )
