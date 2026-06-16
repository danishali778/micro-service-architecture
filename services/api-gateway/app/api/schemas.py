from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=4096)
    tenant_id: str = Field(min_length=1, max_length=120)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    access_token: str = Field(min_length=1)


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int = Field(ge=0)
    subject_id: str
    tenant_id: str
    scopes: list[str]


class MeResponse(BaseModel):
    subject_id: str
    tenant_id: str
    scopes: list[str]


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
    created_at: str
    updated_at: str
    cancelled_at: str | None
    completed_at: str | None
    failed_at: str | None


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: ErrorBody
