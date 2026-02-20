"""
alembic/env.py — Async Alembic environment for InfraHub.

Reads DB_URL from environment via AppSettings (pydantic-settings).
Uses run_async_migrations() pattern with asyncpg driver.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import AppSettings

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide the SQLAlchemy metadata for autogenerate support
# (imported lazily; app models will be registered here in later stories)
target_metadata = None

# Override sqlalchemy.url with the value from AppSettings
# This ensures DB_URL is always read from the environment, never hardcoded
settings = AppSettings()
config.set_main_option("sqlalchemy.url", settings.DB_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no live DB)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within an existing connection context."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (asyncpg driver)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — runs the async loop."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
