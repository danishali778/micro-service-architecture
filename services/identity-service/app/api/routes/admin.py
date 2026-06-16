from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_services, require_admin_context
from app.api.schemas import (
    AssignMembershipRequest,
    AssignMembershipResponse,
    AssignRoleRequest,
    AssignRoleResponse,
    CreateTenantRequest,
    CreateUserRequest,
    CreateUserResponse,
    ErrorResponse,
)
from app.core.container import Services
from app.core.exceptions import ValidationFailedError
from app.security.internal_auth import TrustedInternalContext

router = APIRouter(tags=["admin"])


@router.post(
    "/tenants",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def create_tenant(
    body: CreateTenantRequest,
    _: Annotated[TrustedInternalContext, Depends(require_admin_context)],
    services: Annotated[Services, Depends(get_services)],
) -> dict[str, str]:
    services.create_tenant.execute(
        tenant_id=body.tenant_id,
        slug=body.slug,
        display_name=body.display_name,
    )
    return {"tenant_id": body.tenant_id}


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateUserResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_user(
    body: CreateUserRequest,
    _: Annotated[TrustedInternalContext, Depends(require_admin_context)],
    services: Annotated[Services, Depends(get_services)],
) -> CreateUserResponse:
    if body.create_supabase_user and body.password is None:
        raise ValidationFailedError(
            "Password is required when creating a Supabase user.",
            details=[{"field": "password", "message": "required"}],
        )
    supabase_user_id = await services.create_user.execute(
        user_id=body.user_id,
        supabase_user_id=body.supabase_user_id,
        email=str(body.email),
        display_name=body.display_name,
        create_supabase_user=body.create_supabase_user,
        password=body.password,
    )
    return CreateUserResponse(user_id=body.user_id, supabase_user_id=supabase_user_id)


@router.post(
    "/tenants/{tenant_id}/memberships",
    status_code=status.HTTP_201_CREATED,
    response_model=AssignMembershipResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def assign_membership(
    tenant_id: str,
    body: AssignMembershipRequest,
    _: Annotated[TrustedInternalContext, Depends(require_admin_context)],
    services: Annotated[Services, Depends(get_services)],
) -> AssignMembershipResponse:
    membership_id = services.assign_membership.execute(
        membership_id=body.membership_id,
        tenant_id=tenant_id,
        user_id=body.user_id,
    )
    return AssignMembershipResponse(membership_id=membership_id)


@router.post(
    "/role-assignments",
    status_code=status.HTTP_201_CREATED,
    response_model=AssignRoleResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def assign_role(
    body: AssignRoleRequest,
    _: Annotated[TrustedInternalContext, Depends(require_admin_context)],
    services: Annotated[Services, Depends(get_services)],
) -> AssignRoleResponse:
    role_assignment_id = services.assign_role.execute(
        role_assignment_id=body.role_assignment_id,
        membership_id=body.membership_id,
        role_code=body.role_code,
    )
    return AssignRoleResponse(role_assignment_id=role_assignment_id)
