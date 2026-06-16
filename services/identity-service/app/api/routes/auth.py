from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_services, require_gateway_context
from app.api.schemas import (
    AuthTokenResponse,
    ErrorResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SessionContextResponse,
)
from app.core.container import Services
from app.security.internal_auth import TrustedInternalContext

router = APIRouter(tags=["auth"])


@router.post(
    "/auth/login",
    response_model=AuthTokenResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def login(
    body: LoginRequest,
    _: Annotated[TrustedInternalContext, Depends(require_gateway_context)],
    services: Annotated[Services, Depends(get_services)],
) -> AuthTokenResponse:
    token_set, context = await services.authenticate_user.execute(
        email=str(body.email),
        password=body.password,
        tenant_id=body.tenant_id,
    )
    return AuthTokenResponse(
        access_token=token_set.access_token,
        refresh_token=token_set.refresh_token,
        token_type=token_set.token_type,
        expires_in=token_set.expires_in,
        subject_id=context.subject_id,
        tenant_id=context.tenant_id,
        scopes=sorted(context.scopes),
    )


@router.post(
    "/auth/refresh",
    response_model=AuthTokenResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def refresh(
    body: RefreshRequest,
    _: Annotated[TrustedInternalContext, Depends(require_gateway_context)],
    services: Annotated[Services, Depends(get_services)],
) -> AuthTokenResponse:
    token_set, context = await services.refresh_user_session.execute(
        refresh_token=body.refresh_token,
    )
    return AuthTokenResponse(
        access_token=token_set.access_token,
        refresh_token=token_set.refresh_token,
        token_type=token_set.token_type,
        expires_in=token_set.expires_in,
        subject_id=context.subject_id,
        tenant_id=context.tenant_id,
        scopes=sorted(context.scopes),
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def logout(
    body: LogoutRequest,
    _: Annotated[TrustedInternalContext, Depends(require_gateway_context)],
    services: Annotated[Services, Depends(get_services)],
) -> None:
    await services.logout_user_session.execute(access_token=body.access_token)


@router.get(
    "/auth/session-context",
    response_model=SessionContextResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def session_context(
    _: Annotated[TrustedInternalContext, Depends(require_gateway_context)],
    services: Annotated[Services, Depends(get_services)],
    subject_id: Annotated[str, Query(min_length=1, max_length=120)],
    session_id: Annotated[str, Query(min_length=1, max_length=120)],
) -> SessionContextResponse:
    context = services.resolve_session_context.execute(
        supabase_user_id=subject_id,
        session_id=session_id,
    )
    return SessionContextResponse(
        subject_id=context.subject_id,
        tenant_id=context.tenant_id,
        scopes=sorted(context.scopes),
    )
