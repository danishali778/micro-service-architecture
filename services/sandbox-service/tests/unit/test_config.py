import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_local_header_auth_is_rejected_outside_local_and_test() -> None:
    with pytest.raises(ValidationError, match="local_header"):
        Settings(environment="production", internal_auth_mode="local_header")


def test_local_fake_provider_is_rejected_outside_local_and_test() -> None:
    with pytest.raises(ValidationError, match="local_fake"):
        Settings(
            environment="production",
            internal_auth_mode="deferred",
            sandbox_provider="local_fake",
        )


def test_default_lease_cannot_exceed_max_lease() -> None:
    with pytest.raises(ValidationError, match="DEFAULT_LEASE_SECONDS"):
        Settings(default_lease_seconds=7200, max_lease_seconds=60)


def test_test_environment_accepts_local_shortcuts() -> None:
    settings = Settings(environment="test", internal_auth_mode="local_header")

    assert settings.sandbox_provider == "local_fake"
