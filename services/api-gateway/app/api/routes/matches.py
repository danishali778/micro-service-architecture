from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.api.dependencies import (
    get_services,
    require_matches_cancel,
    require_matches_create,
    require_matches_read,
)
from app.api.schemas import (
    CancelMatchRequest,
    CreateMatchRequest,
    ErrorResponse,
    MatchResponse,
    MatchScenarioResponse,
)
from app.core.container import Services
from app.domain.matches import Match
from app.domain.value_objects.tenant_context import Principal, TrustedRequestContext

router = APIRouter(tags=["matches"])


@router.post(
    "/matches",
    response_model=MatchResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def create_match(
    request: Request,
    body: CreateMatchRequest,
    principal: Annotated[Principal, Depends(require_matches_create)],
    services: Annotated[Services, Depends(get_services)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> MatchResponse:
    match = await services.create_match.execute(
        scenario_id=body.scenario_id,
        scenario_version=body.scenario_version,
        idempotency_key=idempotency_key,
        context=TrustedRequestContext(
            principal=principal,
            correlation_id=request.state.correlation_id,
        ),
    )
    return _match_response(match)


@router.get(
    "/matches/{match_id}",
    response_model=MatchResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def get_match(
    request: Request,
    match_id: str,
    principal: Annotated[Principal, Depends(require_matches_read)],
    services: Annotated[Services, Depends(get_services)],
) -> MatchResponse:
    match = await services.get_match.execute(
        match_id=match_id,
        context=TrustedRequestContext(
            principal=principal,
            correlation_id=request.state.correlation_id,
        ),
    )
    return _match_response(match)


@router.post(
    "/matches/{match_id}/cancel",
    response_model=MatchResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def cancel_match(
    request: Request,
    match_id: str,
    body: CancelMatchRequest,
    principal: Annotated[Principal, Depends(require_matches_cancel)],
    services: Annotated[Services, Depends(get_services)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> MatchResponse:
    match = await services.cancel_match.execute(
        match_id=match_id,
        reason=body.reason,
        idempotency_key=idempotency_key,
        context=TrustedRequestContext(
            principal=principal,
            correlation_id=request.state.correlation_id,
        ),
    )
    return _match_response(match)


def _match_response(match: Match) -> MatchResponse:
    return MatchResponse(
        id=match.id,
        tenant_id=match.tenant_id,
        subject_id=match.subject_id,
        scenario=MatchScenarioResponse(
            id=match.scenario.id,
            version=match.scenario.version,
            snapshot_id=match.scenario.snapshot_id,
            title=match.scenario.title,
        ),
        state=match.state,
        phase=match.phase,
        status_reason=match.status_reason,
        created_at=match.created_at.isoformat(),
        updated_at=match.updated_at.isoformat(),
        cancelled_at=match.cancelled_at.isoformat() if match.cancelled_at else None,
        completed_at=match.completed_at.isoformat() if match.completed_at else None,
        failed_at=match.failed_at.isoformat() if match.failed_at else None,
    )
