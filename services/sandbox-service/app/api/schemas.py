from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class SandboxScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1, max_length=80)
    scenario_id: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)


class ProvisionSandboxRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str = Field(min_length=1, max_length=80)
    scenario: SandboxScenarioRequest
    runtime_template: dict[str, Any] = Field(min_length=1)
    action_policy: dict[str, Any] = Field(min_length=1)
    resource_budget: dict[str, Any] = Field(min_length=1)
    lease_duration_seconds: int | None = Field(default=None, ge=1)


class TerminateSandboxRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="match_cancelled", min_length=1, max_length=200)


class SandboxScenarioResponse(BaseModel):
    snapshot_id: str
    scenario_id: str
    version: str
    title: str


class CleanupResponse(BaseModel):
    status: str
    details: list[dict[str, Any]]


class SandboxResponse(BaseModel):
    id: str
    tenant_id: str
    subject_id: str
    match_id: str
    scenario: SandboxScenarioResponse
    state: str
    status_reason: str
    provider: str
    allocation: dict[str, Any]
    lease_expires_at: datetime
    created_at: datetime
    updated_at: datetime
    ready_at: datetime | None
    terminated_at: datetime | None
    failed_at: datetime | None
    cleanup: CleanupResponse | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: ErrorBody
