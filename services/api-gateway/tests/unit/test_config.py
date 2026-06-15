import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_rejects_local_internal_auth_outside_local_and_test() -> None:
    with pytest.raises(ValidationError, match="local_header internal authentication"):
        Settings(environment="production", internal_auth_mode="local_header")


def test_rejects_wildcard_cors_in_production() -> None:
    with pytest.raises(ValidationError, match="wildcard CORS"):
        Settings(
            environment="production",
            internal_auth_mode="deferred",
            cors_allowed_origins=["*"],
        )


def test_requires_api_prefix_to_start_with_slash() -> None:
    with pytest.raises(ValidationError, match="PUBLIC_API_PREFIX"):
        Settings(public_api_prefix="api/v1")
