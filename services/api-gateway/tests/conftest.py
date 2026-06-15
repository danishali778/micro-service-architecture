from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from app.application.ports.scenario_client import ScenarioClient
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
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
        "oidc_issuer": "https://issuer.test",
        "oidc_discovery_url": "https://issuer.test/.well-known/openid-configuration",
        "oidc_audience": "api-gateway",
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

    async def validate(self, token: str) -> Principal:
        if token != "valid-token":
            raise UnauthorizedError()
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
                    scenario_id="scenario-1",
                    name="Scenario One",
                    description="A safe scenario.",
                    version=1,
                ),
            ),
            next_cursor=cursor,
        )


@pytest.fixture
def token_validator() -> FakeTokenValidator:
    return FakeTokenValidator()


@pytest.fixture
def scenario_client() -> FakeScenarioClient:
    return FakeScenarioClient()


@pytest.fixture
def client(
    token_validator: FakeTokenValidator,
    scenario_client: FakeScenarioClient,
) -> Iterator[TestClient]:
    app = create_app(
        settings=make_test_settings(),
        token_validator=token_validator,
        scenario_client=scenario_client,
    )
    with TestClient(app) as test_client:
        yield test_client
