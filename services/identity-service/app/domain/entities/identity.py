from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionContext:
    subject_id: str
    supabase_user_id: str
    tenant_id: str
    scopes: frozenset[str]


@dataclass(frozen=True, slots=True)
class AuthTokenSet:
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int
    supabase_user_id: str
    session_id: str
    email: str | None


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    decision: str
    reason: str
    policy_version: str
    audit_id: str


@dataclass(frozen=True, slots=True)
class ResourceRef:
    type: str | None
    id: str | None
