from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.exceptions import (
    BadGatewayError,
    ConflictError,
    GatewayTimeoutError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.domain.entities.match import (
    RedRunProposal,
    RedRunResult,
    SandboxProvision,
    ScenarioSnapshot,
)
from app.security.internal_auth import TrustedInternalContext


class _AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: str
    profile_ref: str


class _ProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    proposal_type: str
    title: str
    summary: str
    rationale: str
    action: dict[str, Any]
    expected_signal: str
    risk_level: str
    confidence: float = Field(ge=0, le=1)

    def to_domain(self) -> RedRunProposal:
        return RedRunProposal(
            id=self.proposal_id,
            proposal_type=self.proposal_type,
            title=self.title,
            summary=self.summary,
            rationale=self.rationale,
            action=self.action,
            expected_signal=self.expected_signal,
            risk_level=self.risk_level,
            confidence=self.confidence,
        )


class _RedRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    subject_id: str
    match_id: str
    sandbox_id: str
    scenario: dict[str, str]
    state: str
    status_reason: str
    agent: _AgentResponse
    proposal: _ProposalResponse
    created_at: str
    updated_at: str
    completed_at: str | None
    failed_at: str | None

    def to_domain(self) -> RedRunResult:
        return RedRunResult(
            id=self.id,
            state=self.state,
            adapter=self.agent.adapter,
            profile_ref=self.agent.profile_ref,
            proposal=self.proposal.to_domain(),
        )


class RedAgentHttpClient:
    def __init__(self, *, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")

    async def start_red_run(
        self,
        *,
        match_id: str,
        scenario: ScenarioSnapshot,
        sandbox: SandboxProvision,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> RedRunResult:
        response = await self._request(
            "POST",
            "/internal/v1/red-runs",
            context=context,
            idempotency_key=idempotency_key,
            scopes="red:runs:start",
            json={
                "match_id": match_id,
                "sandbox_id": sandbox.id,
                "scenario": {
                    "snapshot_id": scenario.snapshot_id,
                    "scenario_id": scenario.scenario_id,
                    "version": scenario.version,
                    "title": scenario.title,
                },
                "target_profile": scenario.target_profile,
                "action_policy": scenario.action_policy,
                "resource_budget": scenario.resource_budget,
            },
        )
        return self._parse_red_run(response)

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
                code="red_run_not_found",
                message="The requested red run was not found.",
            )
        if response.status_code == 409:
            raise ConflictError()
        if response.status_code == 504:
            raise GatewayTimeoutError()
        if response.status_code == 503:
            raise ServiceUnavailableError()
        if response.status_code >= 500:
            raise ServiceUnavailableError()
        if response.status_code not in {200, 201, 202}:
            raise BadGatewayError()
        return response

    @staticmethod
    def _parse_red_run(response: httpx.Response) -> RedRunResult:
        try:
            return _RedRunResponse.model_validate_json(response.content).to_domain()
        except ValidationError as error:
            raise BadGatewayError() from error
