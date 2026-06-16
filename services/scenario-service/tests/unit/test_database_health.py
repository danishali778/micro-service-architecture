from app.core.config import Settings
from app.infrastructure.database.health import DatabaseReadinessChecker
from app.infrastructure.database.migrations import CURRENT_MIGRATION_REVISION
from app.security.internal_auth import InternalAuthValidator
from conftest import make_test_settings
from sqlalchemy import create_engine, text


def test_database_readiness_succeeds_with_current_migration() -> None:
    engine = create_engine("sqlite:///:memory:")
    settings = make_test_settings(require_current_migration=True)
    validator = InternalAuthValidator(settings)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": CURRENT_MIGRATION_REVISION},
        )

    try:
        result = DatabaseReadinessChecker(
            engine=engine,
            settings=settings,
            internal_auth_validator=validator,
        ).check()
    finally:
        engine.dispose()

    assert result.ready is True


def test_database_readiness_reports_migration_mismatch() -> None:
    engine = create_engine("sqlite:///:memory:")
    settings = make_test_settings(require_current_migration=True)
    validator = InternalAuthValidator(settings)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('old')"),
        )

    try:
        result = DatabaseReadinessChecker(
            engine=engine,
            settings=settings,
            internal_auth_validator=validator,
        ).check()
    finally:
        engine.dispose()

    assert result.ready is False
    assert result.code == "migration_not_current"


def test_database_readiness_reports_unconfigured_internal_auth() -> None:
    engine = create_engine("sqlite:///:memory:")
    settings = Settings(environment="production", internal_auth_mode="deferred")
    validator = InternalAuthValidator(settings)

    try:
        result = DatabaseReadinessChecker(
            engine=engine,
            settings=settings,
            internal_auth_validator=validator,
        ).check()
    finally:
        engine.dispose()

    assert result.ready is False
    assert result.code == "internal_auth_unconfigured"
