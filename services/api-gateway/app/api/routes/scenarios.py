from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_services, require_scenarios_read
from app.api.schemas import ErrorResponse, ScenarioPageResponse, ScenarioResponse
from app.core.container import Services
from app.domain.value_objects.tenant_context import Principal, TrustedRequestContext

router = APIRouter(tags=["scenarios"])


@router.get(
    "/scenarios",
    response_model=ScenarioPageResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def list_scenarios(
    request: Request,
    principal: Annotated[Principal, Depends(require_scenarios_read)],
    services: Annotated[Services, Depends(get_services)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> ScenarioPageResponse:
    page = await services.list_scenarios.execute(
        limit=limit,
        cursor=cursor,
        context=TrustedRequestContext(
            principal=principal,
            correlation_id=request.state.correlation_id,
        ),
    )
    return ScenarioPageResponse(
        items=[ScenarioResponse.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
    )
