import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from alembic.config import Config

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.core.config import Settings
from app.domain.entities.match import (
    RedRunProposal,
    RedRunResult,
    SandboxProvision,
    ScenarioSnapshot,
)
from app.infrastructure.database.connection import create_session_factory
from app.infrastructure.database.health import StaticReadinessChecker
from app.infrastructure.database.models import Base
from app.infrastructure.database.repositories import SqlAlchemyMatchRepository
from app.main import create_app
from app.security.internal_auth import TrustedInternalContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


def make_test_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": "postgresql+psycopg://match:match@127.0.0.1:5432/match",
        "internal_auth_mode": "local_header",
        "scenario_service_url": "https://scenario.test",
        "red_agent_service_url": "https://red-agent.test",
        "require_current_migration": False,
    }
    values.update(overrides)
    return Settings(**values)


def auth_headers(
    *,
    workload_id: str = "api-gateway",
    subject_id: str = "subject-1",
    tenant_id: str = "tenant-1",
    scopes: str = "matches:create matches:read matches:cancel",
    correlation_id: str = "correlation-1",
) -> dict[str, str]:
    return {
        "X-Internal-Auth-Mode": "local",
        "X-Internal-Workload-ID": workload_id,
        "X-Internal-Subject-ID": subject_id,
        "X-Internal-Tenant-ID": tenant_id,
        "X-Internal-Scopes": scopes,
        "X-Correlation-ID": correlation_id,
    }


def idempotency_headers(key: str = "idem-1") -> dict[str, str]:
    return {"Idempotency-Key": key}


def sample_snapshot(scenario_id: str = "scn_sql_injection_login") -> ScenarioSnapshot:
    return ScenarioSnapshot(
        snapshot_id="ssnap_sql_login_1_0_0",
        scenario_id=scenario_id,
        version="1.0.0",
        title="SQL Injection Login Bypass",
        target_profile={"runtime": "container", "template_ref": "local/sql-login"},
        runtime_template={"kind": "compose", "ref": "local/sql-login/docker-compose.yml"},
        action_policy={"network": "sandbox-only", "filesystem": "workspace-only"},
        resource_budget={"cpu_limit": "1", "memory_mb": 512, "timeout_seconds": 1800},
        verification_contract={"ref": "verify/sql-login/1.0.0"},
    )


@dataclass
class FakeScenarioClient:
    error: Exception | None = None
    calls: list[tuple[str, str | None, TrustedInternalContext]] = field(default_factory=list)

    async def build_snapshot(
        self,
        *,
        scenario_id: str,
        version: str | None,
        context: TrustedInternalContext,
    ) -> ScenarioSnapshot:
        self.calls.append((scenario_id, version, context))
        if self.error is not None:
            raise self.error
        return sample_snapshot(scenario_id)


@dataclass
class FakeSandboxClient:
    error: Exception | None = None
    provision_calls: list[tuple[str, ScenarioSnapshot, str, TrustedInternalContext]] = field(
        default_factory=list
    )
    terminate_calls: list[tuple[str, str, str, TrustedInternalContext]] = field(
        default_factory=list
    )

    async def provision_sandbox(
        self,
        *,
        match_id: str,
        scenario: ScenarioSnapshot,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxProvision:
        self.provision_calls.append((match_id, scenario, idempotency_key, context))
        if self.error is not None:
            raise self.error
        return SandboxProvision(
            id="sandbox_123",
            state="ready",
            provider="local_fake",
            allocation={"allocation_id": "local_sandbox_123"},
        )

    async def terminate_sandbox(
        self,
        *,
        sandbox_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxProvision:
        self.terminate_calls.append((sandbox_id, reason, idempotency_key, context))
        if self.error is not None:
            raise self.error
        return SandboxProvision(
            id=sandbox_id,
            state="terminated",
            provider="local_fake",
            allocation={"allocation_id": f"local_{sandbox_id}"},
        )


@dataclass
class FakeRedAgentClient:
    error: Exception | None = None
    start_calls: list[
        tuple[str, ScenarioSnapshot, SandboxProvision, str, TrustedInternalContext]
    ] = field(default_factory=list)

    async def start_red_run(
        self,
        *,
        match_id: str,
        scenario: ScenarioSnapshot,
        sandbox: SandboxProvision,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> RedRunResult:
        self.start_calls.append((match_id, scenario, sandbox, idempotency_key, context))
        if self.error is not None:
            raise self.error
        return RedRunResult(
            id="redrun_123",
            state="proposal_ready",
            adapter="local_fake",
            profile_ref="red-agent-local-fake@1",
            proposal=RedRunProposal(
                id="attackprop_123",
                proposal_type="http_request",
                title="Probe login form for SQL injection",
                summary="Submit a controlled authentication bypass payload.",
                rationale="The scenario target is a login bypass training target.",
                action={"kind": "http_request", "method": "POST", "path": "/login"},
                expected_signal="Authenticated response.",
                risk_level="training_safe",
                confidence=0.75,
            ),
        )


@pytest.fixture
def scenario_client() -> FakeScenarioClient:
    return FakeScenarioClient()


@pytest.fixture
def sandbox_client() -> FakeSandboxClient:
    return FakeSandboxClient()


@pytest.fixture
def red_agent_client() -> FakeRedAgentClient:
    return FakeRedAgentClient()


@pytest.fixture
def client(
    scenario_client: FakeScenarioClient,
    sandbox_client: FakeSandboxClient,
    red_agent_client: FakeRedAgentClient,
) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = SqlAlchemyMatchRepository(create_session_factory(engine))
    app = create_app(
        settings=make_test_settings(),
        match_repository=repository,
        scenario_client=scenario_client,
        sandbox_client=sandbox_client,
        red_agent_client=red_agent_client,
        readiness_checker=StaticReadinessChecker(),
    )
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


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
