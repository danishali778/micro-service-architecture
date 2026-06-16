from alembic import command
from alembic.config import Config
from app.infrastructure.database.migrations import CURRENT_MIGRATION_REVISION
from sqlalchemy import create_engine, inspect


def test_migrations_apply_from_empty_database(
    alembic_config: Config,
    database_test_url: str,
) -> None:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    engine = create_engine(database_test_url)
    try:
        inspector = inspect(engine)
        assert "scenarios" in inspector.get_table_names()
        assert "scenario_versions" in inspector.get_table_names()
        with engine.connect() as connection:
            version = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
        assert version == CURRENT_MIGRATION_REVISION
    finally:
        engine.dispose()
