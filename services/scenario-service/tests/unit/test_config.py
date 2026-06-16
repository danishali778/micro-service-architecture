import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_rejects_local_header_auth_outside_local_and_test() -> None:
    with pytest.raises(ValidationError, match="local_header internal authentication"):
        Settings(environment="production", internal_auth_mode="local_header")


def test_rejects_default_page_size_larger_than_max() -> None:
    with pytest.raises(ValidationError, match="DEFAULT_PAGE_SIZE"):
        Settings(default_page_size=100, max_page_size=50)


def test_accepts_deferred_auth_for_fail_closed_shared_environment() -> None:
    settings = Settings(environment="production", internal_auth_mode="deferred")

    assert settings.internal_auth_mode == "deferred"
