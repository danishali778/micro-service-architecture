from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migration_applies_from_empty_database(
    alembic_config: Config,
    database_test_url: str,
) -> None:
    engine = create_engine(database_test_url)
    with engine.begin() as connection:
        for table_name in reversed(inspect(connection).get_table_names()):
            connection.exec_driver_sql(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
    engine.dispose()

    assert "red_runs" in tables
    assert "attack_proposals" in tables
    assert "idempotency_records" in tables
