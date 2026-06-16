from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from app.application.ports.identity_client import IdentityClient
from app.application.ports.match_client import MatchClient
from app.application.ports.scenario_client import ScenarioClient
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.domain.auth import AuthTokenResponse
from app.domain.matches import Match, MatchScenario
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
        "match_orchestrator_service_url": "https://matches.test",
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


@dataclass
class FakeMatchClient(MatchClient):
    error: Exception | None = None
    create_calls: list[tuple[str, str | None, str, TrustedRequestContext]] = field(
        default_factory=list
    )
    get_calls: list[tuple[str, TrustedRequestContext]] = field(default_factory=list)
    cancel_calls: list[tuple[str, str, str, TrustedRequestContext]] = field(default_factory=list)

    async def create_match(
        self,
        *,
        scenario_id: str,
        scenario_version: str | None,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match:
        self.create_calls.append((scenario_id, scenario_version, idempotency_key, context))
        if self.error is not None:
            raise self.error
        return _match(scenario_id=scenario_id)

    async def get_match(self, *, match_id: str, context: TrustedRequestContext) -> Match:
        self.get_calls.append((match_id, context))
        if self.error is not None:
            raise self.error
        return _match(match_id=match_id)

    async def cancel_match(
        self,
        *,
        match_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match:
        self.cancel_calls.append((match_id, reason, idempotency_key, context))
        if self.error is not None:
            raise self.error
        return _match(match_id=match_id, state="cancelled", status_reason=reason)


def _match(
    *,
    match_id: str = "match_123",
    scenario_id: str = "scn_sql_injection_login",
    state: str = "waiting_for_sandbox",
    status_reason: str = "scenario_snapshot_created",
) -> Match:
    now = datetime(2026, 6, 16, 11, 0, tzinfo=UTC)
    return Match(
        id=match_id,
        tenant_id="tenant-1",
        subject_id="user-1",
        scenario=MatchScenario(
            id=scenario_id,
            version="1.0.0",
            snapshot_id="ssnap_sql_login_1_0_0",
            title="SQL Injection Login Bypass",
        ),
        state=state,
        phase="setup",
        status_reason=status_reason,
        created_at=now,
        updated_at=now,
        cancelled_at=now if state == "cancelled" else None,
        completed_at=None,
        failed_at=None,
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
def match_client() -> FakeMatchClient:
    return FakeMatchClient()


@pytest.fixture
def client(
    token_validator: FakeTokenValidator,
    identity_client: FakeIdentityClient,
    scenario_client: FakeScenarioClient,
    match_client: FakeMatchClient,
) -> Iterator[TestClient]:
    app = create_app(
        settings=make_test_settings(),
        token_validator=token_validator,
        identity_client=identity_client,
        scenario_client=scenario_client,
        match_client=match_client,
    )
    with TestClient(app) as test_client:
        yield test_client
