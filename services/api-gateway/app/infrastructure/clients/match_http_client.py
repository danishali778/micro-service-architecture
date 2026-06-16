from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.application.ports.internal_auth import InternalAuthenticator
from app.core.exceptions import (
    BadGatewayError,
    ConflictError,
    GatewayTimeoutError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.domain.matches import Match, MatchScenario
from app.domain.value_objects.tenant_context import TrustedRequestContext


class _MatchScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    snapshot_id: str
    title: str


class _MatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    subject_id: str
    scenario: _MatchScenarioResponse
    state: str
    phase: str
    status_reason: str
    created_at: str
    updated_at: str
    cancelled_at: str | None
    completed_at: str | None
    failed_at: str | None

    def to_domain(self) -> Match:
        return Match(
            id=self.id,
            tenant_id=self.tenant_id,
            subject_id=self.subject_id,
            scenario=MatchScenario(
                id=self.scenario.id,
                version=self.scenario.version,
                snapshot_id=self.scenario.snapshot_id,
                title=self.scenario.title,
            ),
            state=self.state,
            phase=self.phase,
            status_reason=self.status_reason,
            created_at=self._datetime(self.created_at),
            updated_at=self._datetime(self.updated_at),
            cancelled_at=self._optional_datetime(self.cancelled_at),
            completed_at=self._optional_datetime(self.completed_at),
            failed_at=self._optional_datetime(self.failed_at),
        )

    @staticmethod
    def _datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @classmethod
    def _optional_datetime(cls, value: str | None) -> datetime | None:
        return cls._datetime(value) if value is not None else None


class MatchHttpClient:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        base_url: str,
        authenticator: InternalAuthenticator,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._authenticator = authenticator

    async def create_match(
        self,
        *,
        scenario_id: str,
        scenario_version: str | None,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match:
        payload: dict[str, str] = {"scenario_id": scenario_id}
        if scenario_version is not None:
            payload["scenario_version"] = scenario_version
        response = await self._request(
            "POST",
            "/internal/v1/matches",
            context=context,
            idempotency_key=idempotency_key,
            json=payload,
        )
        return self._parse_match(response)

    async def get_match(self, *, match_id: str, context: TrustedRequestContext) -> Match:
        response = await self._request(
            "GET",
            f"/internal/v1/matches/{match_id}",
            context=context,
        )
        return self._parse_match(response)

    async def cancel_match(
        self,
        *,
        match_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match:
        response = await self._request(
            "POST",
            f"/internal/v1/matches/{match_id}/cancel",
            context=context,
            idempotency_key=idempotency_key,
            json={"reason": reason},
        )
        return self._parse_match(response)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        context: TrustedRequestContext,
        idempotency_key: str | None = None,
        json: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = self._authenticator.headers(context)
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        try:
            response = await self._http_client.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                json=json,
            )
        except httpx.TimeoutException as error:
            raise GatewayTimeoutError() from error
        except httpx.RequestError as error:
            raise ServiceUnavailableError() from error

        if response.status_code == 404:
            raise NotFoundError(
                code="match_not_found",
                message="The requested match was not found.",
            )
        if response.status_code == 409:
            raise ConflictError()
        if response.status_code >= 500:
            raise ServiceUnavailableError()
        if response.status_code not in {200, 201}:
            raise BadGatewayError()
        return response

    @staticmethod
    def _parse_match(response: httpx.Response) -> Match:
        try:
            return _MatchResponse.model_validate_json(response.content).to_domain()
        except ValidationError as error:
            raise BadGatewayError() from error
