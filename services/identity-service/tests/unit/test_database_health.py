from app.core.config import Settings
from app.infrastructure.database.health import DatabaseReadinessChecker
from app.security.internal_auth import InternalAuthValidator
from sqlalchemy import create_engine


def test_readiness_fails_when_migration_is_missing() -> None:
    engine = create_engine("sqlite:///:memory:")
    checker = DatabaseReadinessChecker(
        engine=engine,
        settings=Settings(environment="test", require_current_migration=True),
        internal_auth_validator=InternalAuthValidator(Settings(environment="test")),
    )

    result = checker.check()

    assert not result.ready
    assert result.code == "database_unavailable"


def test_readiness_fails_when_internal_auth_is_not_configured() -> None:
    engine = create_engine("sqlite:///:memory:")
    checker = DatabaseReadinessChecker(
        engine=engine,
        settings=Settings(
            environment="test",
            internal_auth_mode="deferred",
            require_current_migration=False,
        ),
        internal_auth_validator=InternalAuthValidator(
            Settings(environment="test", internal_auth_mode="deferred")
        ),
    )

    result = checker.check()

    assert not result.ready
    assert result.code == "internal_auth_unconfigured"
