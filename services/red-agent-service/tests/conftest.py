import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.core.config import Settings
from app.infrastructure.agents.local_fake_agent import LocalFakeRedAgent
from app.infrastructure.database.connection import create_session_factory
from app.infrastructure.database.health import StaticReadinessChecker
from app.infrastructure.database.models import Base
from app.infrastructure.database.repositories import SqlAlchemyRedRunRepository
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool


def make_test_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": "postgresql+psycopg://red_agent:red_agent@127.0.0.1:5432/red_agent",
        "internal_auth_mode": "local_header",
        "red_agent_adapter": "local_fake",
        "require_current_migration": False,
    }
    values.update(overrides)
    return Settings(**values)


def auth_headers(
    *,
    workload_id: str = "match-orchestrator-service",
    subject_id: str = "subject-1",
    tenant_id: str = "tenant-1",
    scopes: str = "red:runs:start red:runs:read",
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


def red_run_payload(match_id: str = "match_123") -> dict[str, object]:
    return {
        "match_id": match_id,
        "sandbox_id": "sandbox_123",
        "scenario": {
            "snapshot_id": "ssnap_sql_login_1_0_0",
            "scenario_id": "scn_sql_injection_login",
            "version": "1.0.0",
            "title": "SQL Injection Login Bypass",
        },
        "target_profile": {"runtime": "container", "template_ref": "local/sql-login"},
        "action_policy": {"network": "sandbox-only"},
        "resource_budget": {"cpu_limit": "1", "memory_mb": 512, "timeout_seconds": 1800},
    }


@pytest.fixture()
def engine() -> Iterator[Engine]:
    database_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(database_engine)
    yield database_engine
    database_engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> SqlAlchemyRedRunRepository:
    return SqlAlchemyRedRunRepository(create_session_factory(engine))


@pytest.fixture()
def client(repository: SqlAlchemyRedRunRepository) -> Iterator[TestClient]:
    app = create_app(
        settings=make_test_settings(),
        red_run_repository=repository,
        agent=LocalFakeRedAgent(),
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
