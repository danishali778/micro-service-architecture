from app.core.exceptions import BadGatewayError
from app.domain.value_objects.tenant_context import Principal
from conftest import FakeScenarioClient, FakeTokenValidator
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer valid-token"}


def test_liveness_is_independent_of_readiness(
    client: TestClient, token_validator: FakeTokenValidator
) -> None:
    token_validator.ready = False

    assert client.get("/health/live").json() == {"status": "ok"}
    readiness = client.get("/health/ready")

    assert readiness.status_code == 503
    assert readiness.json()["error"]["code"] == "downstream_unavailable"


def test_readiness_succeeds_after_security_initialization(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_attempts_recovery(
    client: TestClient, token_validator: FakeTokenValidator
) -> None:
    token_validator.ready = False
    token_validator.recover_on_ensure = True

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert token_validator.ensure_ready_calls == 1


def test_default_documentation_routes_are_not_public(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_scenario_listing_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/scenarios")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_scenario_listing_requires_scope(
    client: TestClient, token_validator: FakeTokenValidator
) -> None:
    token_validator.principal = Principal(
        subject_id="user-1",
        tenant_id="tenant-1",
        scopes=frozenset(),
    )

    response = client.get("/api/v1/scenarios", headers=AUTH)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_lists_scenarios_and_propagates_context(
    client: TestClient, scenario_client: FakeScenarioClient
) -> None:
    response = client.get(
        "/api/v1/scenarios?limit=25&cursor=opaque-cursor",
        headers={**AUTH, "X-Correlation-ID": "client-correlation"},
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "client-correlation"
    assert response.json()["next_cursor"] == "opaque-cursor"
    assert response.json()["items"][0]["scenario_id"] == "scenario-1"
    limit, cursor, context = scenario_client.calls[0]
    assert (limit, cursor) == (25, "opaque-cursor")
    assert context.correlation_id == "client-correlation"
    assert context.principal.tenant_id == "tenant-1"


def test_replaces_invalid_correlation_header(client: TestClient) -> None:
    response = client.get(
        "/api/v1/scenarios",
        headers={**AUTH, "X-Correlation-ID": "not safe"},
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] != "not safe"


def test_rejects_invalid_limit_with_stable_error(client: TestClient) -> None:
    response = client.get("/api/v1/scenarios?limit=101", headers=AUTH)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["correlation_id"]


def test_maps_gateway_error_without_leaking_internal_details(
    client: TestClient, scenario_client: FakeScenarioClient
) -> None:
    scenario_client.error = BadGatewayError()

    response = client.get("/api/v1/scenarios", headers=AUTH)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_downstream_response"


def test_unhandled_error_is_sanitized(
    token_validator: FakeTokenValidator,
    scenario_client: FakeScenarioClient,
) -> None:
    from app.main import create_app
    from conftest import make_test_settings

    scenario_client.error = RuntimeError("secret.internal.example")
    app = create_app(
        settings=make_test_settings(),
        token_validator=token_validator,
        scenario_client=scenario_client,
    )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get(
            "/api/v1/scenarios",
            headers={
                **AUTH,
                "Origin": "http://localhost:3000",
                "X-Correlation-ID": "unexpected-error-correlation",
            },
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.headers["X-Correlation-ID"] == "unexpected-error-correlation"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "secret.internal.example" not in response.text
    assert "authorization" not in response.text.lower()
