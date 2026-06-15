from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_services
from app.api.schemas import ErrorResponse, HealthResponse
from app.core.container import Services
from app.core.exceptions import ServiceUnavailableError

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse}},
)
async def readiness(services: Annotated[Services, Depends(get_services)]) -> HealthResponse:
    if not await services.token_validator.ensure_ready():
        raise ServiceUnavailableError("Authentication metadata is not ready.")
    return HealthResponse()
