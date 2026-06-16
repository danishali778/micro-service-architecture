from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.exceptions import (
    BadGatewayError,
    GatewayTimeoutError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.domain.entities.match import ScenarioSnapshot
from app.security.internal_auth import TrustedInternalContext


class _ScenarioSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    scenario_id: str
    version: str
    title: str
    target_profile: dict[str, Any]
    runtime_template: dict[str, Any]
    action_policy: dict[str, Any]
    resource_budget: dict[str, Any]
    verification_contract: dict[str, Any]

    def to_domain(self) -> ScenarioSnapshot:
        return ScenarioSnapshot(
            snapshot_id=self.snapshot_id,
            scenario_id=self.scenario_id,
            version=self.version,
            title=self.title,
            target_profile=self.target_profile,
            runtime_template=self.runtime_template,
            action_policy=self.action_policy,
            resource_budget=self.resource_budget,
            verification_contract=self.verification_contract,
        )


class ScenarioHttpClient:
    def __init__(self, *, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")

    async def build_snapshot(
        self,
        *,
        scenario_id: str,
        version: str | None,
        context: TrustedInternalContext,
    ) -> ScenarioSnapshot:
        payload: dict[str, str] = {"scenario_id": scenario_id}
        if version is not None:
            payload["version"] = version

        try:
            response = await self._http_client.post(
                f"{self._base_url}/internal/v1/scenario-snapshots",
                json=payload,
                headers={
                    "X-Internal-Auth-Mode": "local",
                    "X-Internal-Workload-ID": "match-orchestrator-service",
                    "X-Internal-Subject-ID": context.subject_id,
                    "X-Internal-Tenant-ID": context.tenant_id,
                    "X-Internal-Scopes": " ".join(sorted(context.scopes)),
                    "X-Correlation-ID": context.correlation_id,
                },
            )
        except httpx.TimeoutException as error:
            raise GatewayTimeoutError() from error
        except httpx.RequestError as error:
            raise ServiceUnavailableError() from error

        if response.status_code == 404:
            raise NotFoundError(
                code="scenario_not_found",
                message="The requested scenario was not found.",
            )
        if response.status_code >= 500:
            raise ServiceUnavailableError()
        if response.status_code != 200:
            raise BadGatewayError()

        try:
            return _ScenarioSnapshotResponse.model_validate_json(response.content).to_domain()
        except ValidationError as error:
            raise BadGatewayError() from error
