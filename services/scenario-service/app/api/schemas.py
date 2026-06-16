from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    latest_version: str
    title: str
    summary: str
    difficulty: str
    category: str
    tags: list[str]
    estimated_duration_minutes: int = Field(ge=1)
    status: str


class ScenarioPageResponse(BaseModel):
    items: list[ScenarioResponse]
    next_cursor: str | None


class ScenarioSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1, max_length=80)
    version: str | None = Field(default=None, min_length=1, max_length=32)


class ScenarioSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    scenario_id: str
    version: str
    title: str
    target_profile: dict[str, Any]
    runtime_template: dict[str, Any]
    action_policy: dict[str, Any]
    resource_budget: dict[str, Any]
    verification_contract: dict[str, Any]


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: ErrorBody
