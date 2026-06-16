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
    expires_in: int
    subject_id: str
    tenant_id: str
    scopes: list[str]


class SessionContextResponse(BaseModel):
    subject_id: str
    tenant_id: str
    scopes: list[str]


class CreateTenantRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)


class CreateUserRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    supabase_user_id: str | None = Field(default=None, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=200)
    create_supabase_user: bool = False
    password: str | None = Field(default=None, min_length=1, max_length=4096)


class CreateUserResponse(BaseModel):
    user_id: str
    supabase_user_id: str


class AssignMembershipRequest(BaseModel):
    membership_id: str | None = Field(default=None, max_length=120)
    user_id: str = Field(min_length=1, max_length=120)


class AssignMembershipResponse(BaseModel):
    membership_id: str


class AssignRoleRequest(BaseModel):
    role_assignment_id: str | None = Field(default=None, max_length=120)
    membership_id: str = Field(min_length=1, max_length=120)
    role_code: str = Field(min_length=1, max_length=80)


class AssignRoleResponse(BaseModel):
    role_assignment_id: str


class ResourceRefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str | None = Field(default=None, max_length=120)
    id: str | None = Field(default=None, max_length=160)


class AuthorizationDecisionRequest(BaseModel):
    subject_id: str = Field(min_length=1, max_length=120)
    tenant_id: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=160)
    resource: ResourceRefRequest = Field(default_factory=ResourceRefRequest)
    workload_id: str = Field(min_length=1, max_length=120)


class AuthorizationDecisionResponse(BaseModel):
    decision: str
    reason: str
    policy_version: str
    audit_id: str


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: ErrorBody
