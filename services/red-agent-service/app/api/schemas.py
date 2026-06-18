from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class RedScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1, max_length=120)
    scenario_id: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)


class StartRedRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str = Field(min_length=1, max_length=80)
    sandbox_id: str = Field(min_length=1, max_length=80)
    scenario: RedScenarioRequest
    target_profile: dict[str, Any]
    action_policy: dict[str, Any]
    resource_budget: dict[str, Any]
    agent_profile_ref: str | None = Field(default=None, min_length=1, max_length=160)


class RedScenarioResponse(BaseModel):
    snapshot_id: str
    scenario_id: str
    version: str
    title: str


class AgentResponse(BaseModel):
    adapter: str
    profile_ref: str


class AttackProposalResponse(BaseModel):
    proposal_id: str
    proposal_type: str
    title: str
    summary: str
    rationale: str
    action: dict[str, Any]
    expected_signal: str
    risk_level: str
    confidence: float = Field(ge=0, le=1)


class RedRunResponse(BaseModel):
    id: str
    tenant_id: str
    subject_id: str
    match_id: str
    sandbox_id: str
    scenario: RedScenarioResponse
    state: str
    status_reason: str
    agent: AgentResponse
    proposal: AttackProposalResponse | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    failed_at: datetime | None


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: ErrorBody
