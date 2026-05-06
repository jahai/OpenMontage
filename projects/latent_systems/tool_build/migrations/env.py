"""Alembic environment for latent_systems tool_build v1.

Resolves the SQLite URL dynamically from the script's location so the
migration runs against tool_build/_data/state.db regardless of cwd.

Phase 1 migrations use raw SQL (op.execute) per Section 2; no SQLAlchemy
ORM target_metadata is needed.
"""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve _data/state.db relative to this env.py file (tool_build/migrations/env.py
# → tool_build/_data/state.db is two levels up from env.py).
TOOL_BUILD_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = TOOL_BUILD_DIR / "_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "state.db"
config.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH.as_posix()}")

target_metadata = None  # raw-SQL migrations only in Phase 1


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
