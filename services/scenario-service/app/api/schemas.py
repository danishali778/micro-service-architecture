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


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: ErrorBody
