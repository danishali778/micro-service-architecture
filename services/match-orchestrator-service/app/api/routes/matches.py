from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

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
from app.domain.entities.match import MatchRecord
from app.security.internal_auth import TrustedInternalContext

router = APIRouter(tags=["matches"])


@router.post(
    "/matches",
    response_model=MatchResponse,
    status_code=status.HTTP_201_CREATED,
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
    body: CreateMatchRequest,
    response: Response,
    context: Annotated[TrustedInternalContext, Depends(require_matches_create)],
    services: Annotated[Services, Depends(get_services)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> MatchResponse:
    result = await services.create_match.execute(
        scenario_id=body.scenario_id,
        scenario_version=body.scenario_version,
        idempotency_key=idempotency_key,
        context=context,
    )
    response.status_code = result.status_code
    return _match_response(result.match)


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
def get_match(
    match_id: str,
    context: Annotated[TrustedInternalContext, Depends(require_matches_read)],
    services: Annotated[Services, Depends(get_services)],
) -> MatchResponse:
    return _match_response(services.get_match.execute(match_id=match_id, context=context))


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
    match_id: str,
    body: CancelMatchRequest,
    response: Response,
    context: Annotated[TrustedInternalContext, Depends(require_matches_cancel)],
    services: Annotated[Services, Depends(get_services)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> MatchResponse:
    result = await services.cancel_match.execute(
        match_id=match_id,
        reason=body.reason,
        idempotency_key=idempotency_key,
        context=context,
    )
    response.status_code = result.status_code
    return _match_response(result.match)


def _match_response(match: MatchRecord) -> MatchResponse:
    return MatchResponse(
        id=match.id,
        tenant_id=match.tenant_id,
        subject_id=match.subject_id,
        scenario=MatchScenarioResponse(
            id=match.scenario.scenario_id,
            version=match.scenario.version,
            snapshot_id=match.scenario.snapshot_id,
            title=match.scenario.title,
        ),
        state=match.state,
        phase=match.phase,
        status_reason=match.status_reason,
        created_at=match.created_at,
        updated_at=match.updated_at,
        cancelled_at=match.cancelled_at,
        completed_at=match.completed_at,
        failed_at=match.failed_at,
    )
