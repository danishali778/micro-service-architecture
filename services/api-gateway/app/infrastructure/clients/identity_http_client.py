import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.exceptions import (
    BadGatewayError,
    ForbiddenError,
    GatewayTimeoutError,
    InvalidCredentialsError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.domain.auth import AuthTokenResponse
from app.domain.value_objects.tenant_context import Principal


class _AuthTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int = Field(ge=0)
    subject_id: str
    tenant_id: str
    scopes: list[str]

    def to_domain(self) -> AuthTokenResponse:
        return AuthTokenResponse(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            token_type=self.token_type,
            expires_in=self.expires_in,
            subject_id=self.subject_id,
            tenant_id=self.tenant_id,
            scopes=tuple(self.scopes),
        )


class _SessionContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    tenant_id: str
    scopes: list[str]

    def to_principal(self) -> Principal:
        return Principal(
            subject_id=self.subject_id,
            tenant_id=self.tenant_id,
            scopes=frozenset(self.scopes),
        )


class IdentityHttpClient:
    def __init__(self, *, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")

    async def login(
        self,
        *,
        email: str,
        password: str,
        tenant_id: str,
        correlation_id: str,
    ) -> AuthTokenResponse:
        response = await self._request(
            "POST",
            "/internal/v1/auth/login",
            json={"email": email, "password": password, "tenant_id": tenant_id},
            correlation_id=correlation_id,
        )
        try:
            return _AuthTokenResponse.model_validate_json(response.content).to_domain()
        except ValidationError as error:
            raise BadGatewayError() from error

    async def refresh(self, *, refresh_token: str, correlation_id: str) -> AuthTokenResponse:
        response = await self._request(
            "POST",
            "/internal/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            correlation_id=correlation_id,
        )
        try:
            return _AuthTokenResponse.model_validate_json(response.content).to_domain()
        except ValidationError as error:
            raise BadGatewayError() from error

    async def logout(self, *, access_token: str, correlation_id: str) -> None:
        await self._request(
            "POST",
            "/internal/v1/auth/logout",
            json={"access_token": access_token},
            correlation_id=correlation_id,
        )

    async def resolve_session_context(
        self,
        *,
        subject_id: str,
        session_id: str,
        correlation_id: str,
    ) -> Principal:
        response = await self._request(
            "GET",
            "/internal/v1/auth/session-context",
            params={"subject_id": subject_id, "session_id": session_id},
            correlation_id=correlation_id,
        )
        try:
            return _SessionContextResponse.model_validate_json(response.content).to_principal()
        except ValidationError as error:
            raise BadGatewayError() from error

    async def _request(
        self,
        method: str,
        path: str,
        *,
        correlation_id: str,
        json: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            response = await self._http_client.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                json=json,
                headers={
                    "X-Internal-Auth-Mode": "local",
                    "X-Internal-Workload-ID": "api-gateway",
                    "X-Correlation-ID": correlation_id,
                },
            )
        except httpx.TimeoutException as error:
            raise GatewayTimeoutError() from error
        except httpx.RequestError as error:
            raise ServiceUnavailableError() from error

        if response.status_code == 401:
            if _error_code(response) == "invalid_credentials":
                raise InvalidCredentialsError()
            raise UnauthorizedError()
        if response.status_code == 403:
            raise ForbiddenError()
        if response.status_code >= 500:
            raise ServiceUnavailableError()
        if response.status_code != 200 and response.status_code != 204:
            raise BadGatewayError()
        return response


def _error_code(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None
