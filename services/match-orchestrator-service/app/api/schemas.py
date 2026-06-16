from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class CreateMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1, max_length=80)
    scenario_version: str | None = Field(default=None, min_length=1, max_length=32)


class CancelMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="user_requested", min_length=1, max_length=200)


class MatchScenarioResponse(BaseModel):
    id: str
    version: str
    snapshot_id: str
    title: str


class MatchResponse(BaseModel):
    id: str
    tenant_id: str
    subject_id: str
    scenario: MatchScenarioResponse
    state: str
    phase: str
    status_reason: str
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: ErrorBody
