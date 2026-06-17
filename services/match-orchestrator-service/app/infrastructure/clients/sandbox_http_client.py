from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.exceptions import (
    BadGatewayError,
    ConflictError,
    GatewayTimeoutError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.domain.entities.match import SandboxProvision, ScenarioSnapshot
from app.security.internal_auth import TrustedInternalContext


class _SandboxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    subject_id: str
    match_id: str
    scenario: dict[str, str]
    state: str
    status_reason: str
    provider: str
    allocation: dict[str, Any]
    lease_expires_at: str
    created_at: str
    updated_at: str
    ready_at: str | None
    terminated_at: str | None
    failed_at: str | None
    cleanup: dict[str, Any] | None

    def to_domain(self) -> SandboxProvision:
        return SandboxProvision(
            id=self.id,
            state=self.state,
            provider=self.provider,
            allocation=self.allocation,
        )


class SandboxHttpClient:
    def __init__(self, *, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")

    async def provision_sandbox(
        self,
        *,
        match_id: str,
        scenario: ScenarioSnapshot,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxProvision:
        response = await self._request(
            "POST",
            "/internal/v1/sandboxes",
            context=context,
            idempotency_key=idempotency_key,
            scopes="sandboxes:provision",
            json={
                "match_id": match_id,
                "scenario": {
                    "snapshot_id": scenario.snapshot_id,
                    "scenario_id": scenario.scenario_id,
                    "version": scenario.version,
                    "title": scenario.title,
                },
                "runtime_template": scenario.runtime_template,
                "action_policy": scenario.action_policy,
                "resource_budget": scenario.resource_budget,
                "lease_duration_seconds": _lease_from_budget(scenario.resource_budget),
            },
        )
        return self._parse_sandbox(response)

    async def terminate_sandbox(
        self,
        *,
        sandbox_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxProvision:
        response = await self._request(
            "POST",
            f"/internal/v1/sandboxes/{sandbox_id}/terminate",
            context=context,
            idempotency_key=idempotency_key,
            scopes="sandboxes:terminate",
            json={"reason": reason},
        )
        return self._parse_sandbox(response)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        context: TrustedInternalContext,
        idempotency_key: str,
        scopes: str,
        json: dict[str, Any],
    ) -> httpx.Response:
        try:
            response = await self._http_client.request(
                method,
                f"{self._base_url}{path}",
                headers={
                    "X-Internal-Auth-Mode": "local",
                    "X-Internal-Workload-ID": "match-orchestrator-service",
                    "X-Internal-Subject-ID": context.subject_id,
                    "X-Internal-Tenant-ID": context.tenant_id,
                    "X-Internal-Scopes": scopes,
                    "X-Correlation-ID": context.correlation_id,
                    "Idempotency-Key": idempotency_key,
                },
                json=json,
            )
        except httpx.TimeoutException as error:
            raise GatewayTimeoutError() from error
        except httpx.RequestError as error:
            raise ServiceUnavailableError() from error

        if response.status_code == 404:
            raise NotFoundError(
                code="sandbox_not_found",
                message="The requested sandbox was not found.",
            )
        if response.status_code == 409:
            raise ConflictError()
        if response.status_code >= 500:
            raise ServiceUnavailableError()
        if response.status_code not in {200, 201, 202}:
            raise BadGatewayError()
        return response

    @staticmethod
    def _parse_sandbox(response: httpx.Response) -> SandboxProvision:
        try:
            return _SandboxResponse.model_validate_json(response.content).to_domain()
        except ValidationError as error:
            raise BadGatewayError() from error


def _lease_from_budget(resource_budget: dict[str, Any]) -> int | None:
    value = resource_budget.get("timeout_seconds")
    return value if isinstance(value, int) else None
