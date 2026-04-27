"""Alembic migration environment.

F-077: configured to run against the live SQLAlchemy Base from
``app.database`` and to import ONLY the live model modules
(``app.models.models`` + ``app.models.writing``). The pre-routers
async scaffold's parallel Base in ``app.core.database`` was archived
during F-077 to prevent accidental Base.metadata pollution; do not
add ``from app.core...`` imports here.

DATABASE_URL is read from the environment directly (NOT through the
FastAPI Settings layer) because Alembic runs in a standalone CLI
context and shouldn't take a load-time dependency on app config.
The default points at the docker-compose Postgres so the bare
``alembic upgrade head`` works on a fresh checkout.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Importing the model modules registers every Class(Base) on
# Base.metadata via SQLAlchemy's declarative side effect — we don't
# need to USE the imported names. Keep this list aligned with the
# live model files; do NOT add ``app.core`` or any archive/* path.
from app.database import Base
from app.models import models as _models  # noqa: F401 — side-effect: register tables
from app.models import writing as _writing_models  # noqa: F401 — side-effect: register tables

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url",
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://fluentpath:fluentpath_local_dev@localhost:5432/fluentpath",
    ),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
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
    """Run migrations in 'online' mode (against a live connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
