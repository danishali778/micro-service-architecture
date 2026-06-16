import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import jwt
import pytest
from alembic.config import Config

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.application.ports.identity_repository import IdentityRepository
from app.application.ports.supabase_auth import SupabaseAuthProvider
from app.core.config import Settings
from app.domain.entities.identity import (
    AuthorizationDecision,
    AuthTokenSet,
    ResourceRef,
    SessionContext,
)
from app.infrastructure.database.health import StaticReadinessChecker
from app.main import create_app
from fastapi.testclient import TestClient


def make_test_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": "postgresql+psycopg://identity:identity@127.0.0.1:5432/identity",
        "internal_auth_mode": "local_header",
        "require_current_migration": False,
        "supabase_auth_url": "https://supabase.test/auth/v1",
        "supabase_jwt_issuer": "https://supabase.test/auth/v1",
        "supabase_jwks_url": "https://supabase.test/auth/v1/.well-known/jwks.json",
    }
    values.update(overrides)
    return Settings(**values)


def auth_headers(
    *,
    workload_id: str = "api-gateway",
    correlation_id: str = "correlation-1",
) -> dict[str, str]:
    return {
        "X-Internal-Auth-Mode": "local",
        "X-Internal-Workload-ID": workload_id,
        "X-Correlation-ID": correlation_id,
    }


def make_access_token(
    *,
    supabase_user_id: str = "supabase-user-1",
    session_id: str = "session-1",
) -> str:
    return jwt.encode(
        {
            "sub": supabase_user_id,
            "session_id": session_id,
        },
        "test-secret",
        algorithm="HS256",
    )


@dataclass
class FakeSupabaseAuthProvider(SupabaseAuthProvider):
    error: Exception | None = None
    login_calls: list[tuple[str, str]] = field(default_factory=list)
    refresh_calls: list[str] = field(default_factory=list)
    logout_calls: list[str] = field(default_factory=list)
    create_user_calls: list[tuple[str, str]] = field(default_factory=list)
    token_set: AuthTokenSet = field(
        default_factory=lambda: AuthTokenSet(
            access_token=make_access_token(),
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=3600,
            supabase_user_id="supabase-user-1",
            session_id="session-1",
            email="learner@example.com",
        )
    )

    async def login_with_password(self, *, email: str, password: str) -> AuthTokenSet:
        self.login_calls.append((email, password))
        if self.error is not None:
            raise self.error
        return self.token_set

    async def refresh_session(self, *, refresh_token: str) -> AuthTokenSet:
        self.refresh_calls.append(refresh_token)
        if self.error is not None:
            raise self.error
        return self.token_set

    async def logout(self, *, access_token: str) -> None:
        self.logout_calls.append(access_token)
        if self.error is not None:
            raise self.error

    async def create_user(self, *, email: str, password: str) -> str:
        self.create_user_calls.append((email, password))
        if self.error is not None:
            raise self.error
        return "created-supabase-user"


@dataclass
class FakeIdentityRepository(IdentityRepository):
    active_context: bool = True
    context: SessionContext = field(
        default_factory=lambda: SessionContext(
            subject_id="user-1",
            supabase_user_id="supabase-user-1",
            tenant_id="tenant-1",
            scopes=frozenset({"scenarios:read", "matches:read"}),
        )
    )
    recorded_sessions: list[tuple[str, str, str, str]] = field(default_factory=list)
    revoked_sessions: list[tuple[str, str]] = field(default_factory=list)
    tenants: list[tuple[str, str, str]] = field(default_factory=list)
    users: list[tuple[str, str, str, str | None]] = field(default_factory=list)
    memberships: list[tuple[str, str, str]] = field(default_factory=list)
    roles: list[tuple[str, str, frozenset[str]]] = field(default_factory=list)
    role_assignments: list[tuple[str, str, str]] = field(default_factory=list)

    def session_context_for_login(
        self,
        *,
        supabase_user_id: str,
        tenant_id: str,
    ) -> SessionContext | None:
        if not self.active_context or tenant_id != self.context.tenant_id:
            return None
        return self.context if supabase_user_id == self.context.supabase_user_id else None

    def session_context_for_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
    ) -> SessionContext | None:
        if not self.active_context or session_id != "session-1":
            return None
        return self.context if supabase_user_id == self.context.supabase_user_id else None

    def session_context_for_subject_tenant(
        self,
        *,
        subject_id: str,
        tenant_id: str,
    ) -> SessionContext | None:
        if not self.active_context or tenant_id != self.context.tenant_id:
            return None
        return self.context if subject_id == self.context.subject_id else None

    def record_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> None:
        self.recorded_sessions.append((supabase_user_id, session_id, tenant_id, user_id))

    def revoke_session(self, *, supabase_user_id: str, session_id: str) -> None:
        self.revoked_sessions.append((supabase_user_id, session_id))

    def create_tenant(self, *, tenant_id: str, slug: str, display_name: str) -> None:
        self.tenants.append((tenant_id, slug, display_name))

    def create_user(
        self,
        *,
        user_id: str,
        supabase_user_id: str,
        email: str,
        display_name: str | None,
    ) -> None:
        self.users.append((user_id, supabase_user_id, email, display_name))

    def assign_membership(self, *, membership_id: str, tenant_id: str, user_id: str) -> None:
        self.memberships.append((membership_id, tenant_id, user_id))

    def create_role(self, *, role_code: str, display_name: str, scopes: frozenset[str]) -> None:
        self.roles.append((role_code, display_name, scopes))

    def assign_role(
        self,
        *,
        role_assignment_id: str,
        membership_id: str,
        role_code: str,
    ) -> None:
        self.role_assignments.append((role_assignment_id, membership_id, role_code))

    def evaluate_authorization(
        self,
        *,
        subject_id: str,
        tenant_id: str,
        workload_id: str,
        action: str,
        resource: ResourceRef,
        required_scope: str,
        correlation_id: str,
    ) -> AuthorizationDecision:
        context = self.session_context_for_subject_tenant(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )
        decision = "allow" if context and required_scope in context.scopes else "deny"
        return AuthorizationDecision(
            decision=decision,
            reason="scope_present" if decision == "allow" else "missing_permission",
            policy_version="identity-policy-v1",
            audit_id="audit-1",
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def auth_provider() -> FakeSupabaseAuthProvider:
    return FakeSupabaseAuthProvider()


@pytest.fixture
def repository() -> FakeIdentityRepository:
    return FakeIdentityRepository()


@pytest.fixture
def client(
    auth_provider: FakeSupabaseAuthProvider,
    repository: FakeIdentityRepository,
) -> Iterator[TestClient]:
    app = create_app(
        settings=make_test_settings(),
        repository=repository,
        auth_provider=auth_provider,
        readiness_checker=StaticReadinessChecker(),
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def database_test_url() -> str:
    value = os.environ.get("DATABASE_TEST_URL")
    if value is None:
        pytest.skip("DATABASE_TEST_URL is not configured")
    return value


@pytest.fixture(scope="session")
def service_root() -> Path:
    return SERVICE_ROOT


@pytest.fixture()
def alembic_config(service_root: Path, database_test_url: str) -> Config:
    config = Config(str(service_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_test_url)
    config.attributes["database_url"] = database_test_url
    return config
