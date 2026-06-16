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
from app.domain.entities.scenario import ScenarioCatalogItem, ScenarioPage
from app.infrastructure.database.health import StaticReadinessChecker
from app.main import create_app
from fastapi.testclient import TestClient


def make_test_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": "postgresql+psycopg://scenario:scenario@127.0.0.1:5432/scenario",
        "internal_auth_mode": "local_header",
        "require_current_migration": False,
    }
    values.update(overrides)
    return Settings(**values)


def auth_headers(
    *,
    workload_id: str = "api-gateway",
    subject_id: str = "subject-1",
    tenant_id: str = "tenant-1",
    scopes: str = "scenarios:read",
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


@dataclass
class FakeScenarioRepository:
    error: Exception | None = None
    calls: list[tuple[str, int, int]] = field(default_factory=list)
    page: ScenarioPage = field(
        default_factory=lambda: ScenarioPage(
            items=(
                ScenarioCatalogItem(
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
            next_cursor=None,
        )
    )

    def list_visible_published(
        self,
        *,
        tenant_id: str,
        limit: int,
        offset: int,
    ) -> ScenarioPage:
        self.calls.append((tenant_id, limit, offset))
        if self.error is not None:
            raise self.error
        return self.page


@pytest.fixture
def scenario_repository() -> FakeScenarioRepository:
    return FakeScenarioRepository()


@pytest.fixture
def client(scenario_repository: FakeScenarioRepository) -> Iterator[TestClient]:
    app = create_app(
        settings=make_test_settings(),
        scenario_repository=scenario_repository,
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
