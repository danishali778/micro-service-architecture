import time

import httpx
import jwt
import pytest
from app.core.exceptions import InvalidCredentialsError, UpstreamTimeoutError
from app.infrastructure.auth.supabase_http_client import SupabaseHttpAuthProvider
from conftest import make_test_settings


def _token() -> str:
    return jwt.encode(
        {
            "sub": "supabase-user-1",
            "session_id": "session-1",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        "test-secret",
        algorithm="HS256",
    )


@pytest.mark.anyio
async def test_login_with_password_calls_supabase_auth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/token"
        assert request.url.params["grant_type"] == "password"
        assert request.headers["apikey"] == "local-anon-key"
        return httpx.Response(
            200,
            json={
                "access_token": _token(),
                "refresh_token": "refresh-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": "supabase-user-1", "email": "learner@example.com"},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        provider = SupabaseHttpAuthProvider(
            http_client=http_client,
            settings=make_test_settings(),
        )
        token_set = await provider.login_with_password(
            email="learner@example.com",
            password="secret-password",
        )

    assert token_set.supabase_user_id == "supabase-user-1"
    assert token_set.session_id == "session-1"


@pytest.mark.anyio
async def test_invalid_supabase_credentials_map_to_generic_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        provider = SupabaseHttpAuthProvider(
            http_client=http_client,
            settings=make_test_settings(),
        )
        with pytest.raises(InvalidCredentialsError):
            await provider.login_with_password(
                email="learner@example.com",
                password="wrong-password",
            )


@pytest.mark.anyio
async def test_supabase_timeout_maps_to_504() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        provider = SupabaseHttpAuthProvider(
            http_client=http_client,
            settings=make_test_settings(),
        )
        with pytest.raises(UpstreamTimeoutError):
            await provider.refresh_session(refresh_token="refresh-token")
