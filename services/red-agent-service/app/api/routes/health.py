from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_services
from app.api.schemas import ErrorResponse, HealthResponse
from app.core.container import Services
from app.core.exceptions import ServiceUnavailableError

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse}},
)
def ready(services: Annotated[Services, Depends(get_services)]) -> HealthResponse:
    result = services.readiness_checker.check()
    if not result.ready:
        raise ServiceUnavailableError(result.message, code=result.code)
    return HealthResponse()
