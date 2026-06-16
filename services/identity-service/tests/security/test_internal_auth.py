import pytest
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.security.internal_auth import InternalAuthValidator
from starlette.requests import Request


def test_local_header_auth_rejected_when_deferred() -> None:
    validator = InternalAuthValidator(Settings(environment="test", internal_auth_mode="deferred"))
    scope = {
        "type": "http",
        "headers": [
            (b"x-internal-auth-mode", b"local"),
            (b"x-internal-workload-id", b"api-gateway"),
        ],
    }
    request = Request(scope)
    request.state.correlation_id = "correlation-1"

    with pytest.raises(ServiceUnavailableError):
        validator.authenticate(request)
