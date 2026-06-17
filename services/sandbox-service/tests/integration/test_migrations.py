from alembic import command
from alembic.config import Config


def test_alembic_upgrade_from_empty_database(alembic_config: Config) -> None:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
