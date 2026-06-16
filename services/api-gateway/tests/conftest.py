from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from app.application.ports.identity_client import IdentityClient
from app.application.ports.scenario_client import ScenarioClient
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.domain.auth import AuthTokenResponse
from app.domain.scenarios import Scenario, ScenarioPage
from app.domain.value_objects.tenant_context import Principal, TrustedRequestContext
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_test_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "supabase_jwt_issuer": "https://issuer.test/auth/v1",
        "supabase_jwks_url": "https://issuer.test/auth/v1/.well-known/jwks.json",
        "supabase_jwt_audience": "authenticated",
        "identity_service_url": "https://identity.test",
        "scenario_service_url": "https://scenario.test",
        "internal_auth_mode": "local_header",
    }
    values.update(overrides)
    return Settings(**values)


@dataclass
class FakeTokenValidator:
    ready: bool = True
    recover_on_ensure: bool = False
    ensure_ready_calls: int = 0
    principal: Principal = field(
        default_factory=lambda: Principal(
            subject_id="user-1",
            tenant_id="tenant-1",
            scopes=frozenset({"scenarios:read"}),
        )
    )

    @property
    def is_ready(self) -> bool:
        return self.ready

    async def initialize(self) -> None:
        return None

    async def ensure_ready(self) -> bool:
        self.ensure_ready_calls += 1
        if self.recover_on_ensure:
            self.ready = True
        return self.ready

    async def validate(self, token: str, *, correlation_id: str) -> Principal:
        if token != "valid-token":
            raise UnauthorizedError()
        return self.principal


@dataclass
class FakeIdentityClient(IdentityClient):
    error: Exception | None = None
    login_calls: list[tuple[str, str, str, str]] = field(default_factory=list)
    refresh_calls: list[tuple[str, str]] = field(default_factory=list)
    logout_calls: list[tuple[str, str]] = field(default_factory=list)
    context_calls: list[tuple[str, str, str]] = field(default_factory=list)
    principal: Principal = field(
        default_factory=lambda: Principal(
            subject_id="user-1",
            tenant_id="tenant-1",
            scopes=frozenset({"scenarios:read"}),
        )
    )

    async def login(
        self,
        *,
        email: str,
        password: str,
        tenant_id: str,
        correlation_id: str,
    ) -> AuthTokenResponse:
        self.login_calls.append((email, password, tenant_id, correlation_id))
        if self.error is not None:
            raise self.error
        return AuthTokenResponse(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=3600,
            subject_id="user-1",
            tenant_id=tenant_id,
            scopes=("scenarios:read",),
        )

    async def refresh(self, *, refresh_token: str, correlation_id: str) -> AuthTokenResponse:
        self.refresh_calls.append((refresh_token, correlation_id))
        if self.error is not None:
            raise self.error
        return AuthTokenResponse(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            token_type="bearer",
            expires_in=3600,
            subject_id="user-1",
            tenant_id="tenant-1",
            scopes=("scenarios:read",),
        )

    async def logout(self, *, access_token: str, correlation_id: str) -> None:
        self.logout_calls.append((access_token, correlation_id))
        if self.error is not None:
            raise self.error

    async def resolve_session_context(
        self,
        *,
        subject_id: str,
        session_id: str,
        correlation_id: str,
    ) -> Principal:
        self.context_calls.append((subject_id, session_id, correlation_id))
        if self.error is not None:
            raise self.error
        return self.principal


@dataclass
class FakeScenarioClient(ScenarioClient):
    error: Exception | None = None
    calls: list[tuple[int, str | None, TrustedRequestContext]] = field(default_factory=list)

    async def list_scenarios(
        self,
        *,
        limit: int,
        cursor: str | None,
        context: TrustedRequestContext,
    ) -> ScenarioPage:
        self.calls.append((limit, cursor, context))
        if self.error is not None:
            raise self.error
        return ScenarioPage(
            items=(
                Scenario(
                    id="scn_sql_injection_login",
                    latest_version="1.0.0",
                    title="SQL Injection Login Bypass",
                    summary="Find and exploit an injectable login form.",
                    difficulty="beginner",
                    category="web-security",
                    tags=("sql-injection", "authentication"),
                    estimated_duration_minutes=30,
                    status="published",
                ),
            ),
            next_cursor=cursor,
        )


@pytest.fixture
def token_validator() -> FakeTokenValidator:
    return FakeTokenValidator()


@pytest.fixture
def identity_client() -> FakeIdentityClient:
    return FakeIdentityClient()


@pytest.fixture
def scenario_client() -> FakeScenarioClient:
    return FakeScenarioClient()


@pytest.fixture
def client(
    token_validator: FakeTokenValidator,
    identity_client: FakeIdentityClient,
    scenario_client: FakeScenarioClient,
) -> Iterator[TestClient]:
    app = create_app(
        settings=make_test_settings(),
        token_validator=token_validator,
        identity_client=identity_client,
        scenario_client=scenario_client,
    )
    with TestClient(app) as test_client:
        yield test_client
