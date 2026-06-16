from app.domain.value_objects.pagination import encode_offset_cursor
from app.infrastructure.database.health import StaticReadinessChecker
from app.main import create_app
from conftest import FakeScenarioRepository, auth_headers, make_test_settings
from fastapi.testclient import TestClient


def test_liveness_returns_ok(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_unavailable_when_not_ready(
    scenario_repository: FakeScenarioRepository,
) -> None:
    app = create_app(
        settings=make_test_settings(),
        scenario_repository=scenario_repository,
        readiness_checker=StaticReadinessChecker(ready=False, code="database_unavailable"),
    )

    with TestClient(app) as test_client:
        response = test_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"


def test_lists_scenarios_and_propagates_context(
    client: TestClient,
    scenario_repository: FakeScenarioRepository,
) -> None:
    response = client.get(
        f"/internal/v1/scenarios?limit=25&cursor={encode_offset_cursor(50)}",
        headers=auth_headers(tenant_id="tenant-abc"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["id"] == "scn_sql_injection_login"
    assert body["items"][0]["latest_version"] == "1.0.0"
    assert body["items"][0]["tags"] == ["sql-injection", "authentication"]
    assert response.headers["X-Correlation-ID"] == "correlation-1"
    assert scenario_repository.calls == [("tenant-abc", 25, 50)]


def test_rejects_invalid_limit(client: TestClient) -> None:
    response = client.get("/internal/v1/scenarios?limit=101", headers=auth_headers())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_rejects_invalid_cursor(client: TestClient) -> None:
    response = client.get("/internal/v1/scenarios?cursor=bad-cursor", headers=auth_headers())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_builds_scenario_snapshot_for_orchestrator(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/scenario-snapshots",
        json={"scenario_id": "scn_sql_injection_login", "version": "1.0.0"},
        headers=auth_headers(
            workload_id="match-orchestrator-service",
            scopes="matches:create",
            tenant_id="tenant-abc",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_id"] == "ssnap_sql_login_1_0_0"
    assert body["scenario_id"] == "scn_sql_injection_login"
    assert body["target_profile"]["runtime"] == "container"
    assert response.headers["X-Correlation-ID"] == "correlation-1"


def test_snapshot_returns_not_found_for_unavailable_scenario(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/scenario-snapshots",
        json={"scenario_id": "missing"},
        headers=auth_headers(workload_id="match-orchestrator-service", scopes="matches:create"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "scenario_not_found"


def test_unexpected_errors_do_not_leak_internal_details(
    scenario_repository: FakeScenarioRepository,
) -> None:
    scenario_repository.error = RuntimeError("secret.internal.database")
    app = create_app(
        settings=make_test_settings(),
        scenario_repository=scenario_repository,
        readiness_checker=StaticReadinessChecker(),
    )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/internal/v1/scenarios", headers=auth_headers())

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "secret.internal.database" not in response.text
