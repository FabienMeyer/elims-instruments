"""Alembic migration environment."""

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import elims_instruments.database  # noqa: F401

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating an engine."""
    context.configure(
        url=context.config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a supplied or configured connection."""
    connection = context.config.attributes.get("connection")
    if connection is not None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        context.config.get_section(context.config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as configured_connection:
        context.configure(
            connection=configured_connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
