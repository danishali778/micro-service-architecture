import pytest
from app.core.config import Settings
from conftest import make_test_settings
from pydantic import ValidationError


def test_local_defaults_are_valid() -> None:
    settings = make_test_settings()

    assert settings.service_name == "red-agent-service"
    assert settings.red_agent_adapter == "local_fake"


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_rejects_local_header_outside_local_and_test(environment: str) -> None:
    with pytest.raises(ValidationError):
        Settings(environment=environment, internal_auth_mode="local_header")


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_rejects_local_fake_outside_local_and_test(environment: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment=environment, internal_auth_mode="deferred", red_agent_adapter="local_fake"
        )
