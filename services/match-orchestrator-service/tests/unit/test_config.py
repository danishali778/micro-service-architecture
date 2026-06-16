import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_local_header_auth_is_rejected_outside_local_and_test() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", internal_auth_mode="local_header")


def test_internal_api_prefix_must_start_with_slash() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="test", internal_api_prefix="internal/v1")
