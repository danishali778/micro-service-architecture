from app.infrastructure.database.health import StaticReadinessChecker
from app.main import create_app
from conftest import make_test_settings
from fastapi.testclient import TestClient


def test_readiness_failure_uses_stable_error_shape() -> None:
    app = create_app(
        settings=make_test_settings(),
        readiness_checker=StaticReadinessChecker(ready=False, code="database_unavailable"),
    )

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
