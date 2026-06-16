import os
from logging.config import fileConfig
from typing import cast

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.infrastructure.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    attribute_url = cast(str | None, config.attributes.get("database_url"))
    if attribute_url is not None:
        return attribute_url

    url = os.environ.get(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url"),
    )
    if url is None:
        raise RuntimeError("DATABASE_URL or sqlalchemy.url must be configured")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
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
