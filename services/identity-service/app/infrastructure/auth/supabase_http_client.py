from typing import Any

import httpx
import jwt
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    InvalidCredentialsError,
    ServiceUnavailableError,
    UpstreamTimeoutError,
)
from app.domain.entities.identity import AuthTokenSet


class _SupabaseUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    email: str | None = None


class _SupabaseTokenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a secret.
    expires_in: int = Field(default=0, ge=0)
    user: _SupabaseUser | None = None


class _SupabaseAdminUserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str


class SupabaseHttpAuthProvider:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        settings: Settings,
    ) -> None:
        self._http_client = http_client
        self._settings = settings
        self._base_url = str(settings.supabase_auth_url).rstrip("/")

    async def login_with_password(self, *, email: str, password: str) -> AuthTokenSet:
        response = await self._request(
            "POST",
            "/token",
            params={"grant_type": "password"},
            json={"email": email, "password": password},
            use_service_role=False,
        )
        return self._parse_token_response(response)

    async def refresh_session(self, *, refresh_token: str) -> AuthTokenSet:
        response = await self._request(
            "POST",
            "/token",
            params={"grant_type": "refresh_token"},
            json={"refresh_token": refresh_token},
            use_service_role=False,
        )
        return self._parse_token_response(response)

    async def logout(self, *, access_token: str) -> None:
        await self._request(
            "POST",
            "/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
            use_service_role=False,
        )

    async def create_user(self, *, email: str, password: str) -> str:
        response = await self._request(
            "POST",
            "/admin/users",
            json={"email": email, "password": password, "email_confirm": True},
            use_service_role=True,
        )
        try:
            return _SupabaseAdminUserResponse.model_validate_json(response.content).id
        except ValidationError as error:
            raise ServiceUnavailableError(
                "Supabase Auth returned an invalid user response."
            ) from error

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        use_service_role: bool,
    ) -> httpx.Response:
        api_key = (
            self._settings.supabase_service_role_key
            if use_service_role
            else self._settings.supabase_anon_key
        )
        if api_key is None:
            raise ServiceUnavailableError("Supabase service role key is not configured.")

        request_headers = {
            "apikey": api_key.get_secret_value(),
            "Content-Type": "application/json",
        }
        if use_service_role:
            request_headers["Authorization"] = f"Bearer {api_key.get_secret_value()}"
        if headers:
            request_headers.update(headers)

        try:
            response = await self._http_client.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                json=json,
                headers=request_headers,
            )
        except httpx.TimeoutException as error:
            raise UpstreamTimeoutError() from error
        except httpx.RequestError as error:
            raise ServiceUnavailableError("Supabase Auth is unavailable.") from error

        if response.status_code in {400, 401, 403}:
            raise InvalidCredentialsError()
        if response.status_code >= 500:
            raise ServiceUnavailableError("Supabase Auth is unavailable.")
        if response.status_code >= 400:
            raise ServiceUnavailableError("Supabase Auth request failed.")
        return response

    def _parse_token_response(self, response: httpx.Response) -> AuthTokenSet:
        try:
            parsed = _SupabaseTokenResponse.model_validate_json(response.content)
            claims = _unverified_claims(parsed.access_token)
        except (ValidationError, jwt.InvalidTokenError) as error:
            raise ServiceUnavailableError(
                "Supabase Auth returned an invalid token response."
            ) from error

        subject = claims.get("sub")
        session_id = claims.get("session_id")
        if not isinstance(subject, str) or not subject:
            raise ServiceUnavailableError("Supabase Auth token is missing subject.")
        if not isinstance(session_id, str) or not session_id:
            raise ServiceUnavailableError("Supabase Auth token is missing session ID.")

        if parsed.user is not None and parsed.user.id != subject:
            raise ServiceUnavailableError("Supabase Auth token subject does not match user.")

        return AuthTokenSet(
            access_token=parsed.access_token,
            refresh_token=parsed.refresh_token,
            token_type=parsed.token_type,
            expires_in=parsed.expires_in,
            supabase_user_id=subject,
            session_id=session_id,
            email=parsed.user.email if parsed.user is not None else None,
        )


def _unverified_claims(token: str) -> dict[str, Any]:
    claims = jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_aud": False,
            "verify_exp": False,
            "verify_nbf": False,
            "verify_iat": False,
        },
    )
    if not isinstance(claims, dict):
        raise jwt.InvalidTokenError("JWT claims must be an object")
    return claims
