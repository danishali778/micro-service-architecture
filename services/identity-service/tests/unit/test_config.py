import pytest
from app.core.config import Settings


def test_rejects_local_internal_auth_outside_local_and_test() -> None:
    with pytest.raises(ValueError, match="local_header"):
        Settings(environment="staging", internal_auth_mode="local_header")


def test_rejects_shared_secret_jwt_algorithm() -> None:
    with pytest.raises(ValueError, match="shared-secret"):
        Settings(supabase_jwt_algorithms="RS256,HS256")


def test_accepts_local_supabase_http_urls_in_test() -> None:
    settings = Settings(environment="test")

    assert settings.allowed_jwt_algorithms == ("RS256", "ES256")
