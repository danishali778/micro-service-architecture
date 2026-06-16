from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_principal, get_services
from app.api.schemas import (
    AuthTokenResponse,
    ErrorResponse,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
)
from app.core.container import Services
from app.domain.value_objects.tenant_context import Principal

router = APIRouter(tags=["auth"])


@router.post(
    "/auth/login",
    response_model=AuthTokenResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def login(
    request: Request,
    body: LoginRequest,
    services: Annotated[Services, Depends(get_services)],
) -> AuthTokenResponse:
    tokens = await services.identity_client.login(
        email=body.email,
        password=body.password,
        tenant_id=body.tenant_id,
        correlation_id=request.state.correlation_id,
    )
    return AuthTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        subject_id=tokens.subject_id,
        tenant_id=tokens.tenant_id,
        scopes=list(tokens.scopes),
    )


@router.post(
    "/auth/refresh",
    response_model=AuthTokenResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def refresh(
    request: Request,
    body: RefreshRequest,
    services: Annotated[Services, Depends(get_services)],
) -> AuthTokenResponse:
    tokens = await services.identity_client.refresh(
        refresh_token=body.refresh_token,
        correlation_id=request.state.correlation_id,
    )
    return AuthTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        subject_id=tokens.subject_id,
        tenant_id=tokens.tenant_id,
        scopes=list(tokens.scopes),
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def logout(
    request: Request,
    body: LogoutRequest,
    services: Annotated[Services, Depends(get_services)],
) -> None:
    await services.identity_client.logout(
        access_token=body.access_token,
        correlation_id=request.state.correlation_id,
    )


@router.get(
    "/auth/me",
    response_model=MeResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def me(principal: Annotated[Principal, Depends(get_principal)]) -> MeResponse:
    return MeResponse(
        subject_id=principal.subject_id,
        tenant_id=principal.tenant_id,
        scopes=sorted(principal.scopes),
    )
