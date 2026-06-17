import httpx
import pytest
from app.core.exceptions import (
    BadGatewayError,
    ConflictError,
    GatewayTimeoutError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.domain.value_objects.tenant_context import Principal, TrustedRequestContext
from app.infrastructure.clients.local_internal_auth import LocalHeaderAuthenticator
from app.infrastructure.clients.match_http_client import MatchHttpClient

CONTEXT = TrustedRequestContext(
    principal=Principal(
        subject_id="subject-1",
        tenant_id="tenant-1",
        scopes=frozenset({"matches:create", "matches:read", "matches:cancel"}),
    ),
    correlation_id="correlation-1",
)


def _match_payload() -> dict[str, object]:
    return {
        "id": "match_123",
        "tenant_id": "tenant-1",
        "subject_id": "subject-1",
        "scenario": {
            "id": "scn_sql_injection_login",
            "version": "1.0.0",
            "snapshot_id": "ssnap_sql_login_1_0_0",
            "title": "SQL Injection Login Bypass",
        },
        "state": "sandbox_ready",
        "phase": "setup",
        "status_reason": "scenario_snapshot_created",
        "created_at": "2026-06-16T11:00:00+00:00",
        "updated_at": "2026-06-16T11:00:00+00:00",
        "cancelled_at": None,
        "completed_at": None,
        "failed_at": None,
    }


@pytest.mark.anyio
async def test_match_client_propagates_auth_context_and_idempotency_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/v1/matches"
        assert request.headers["X-Internal-Workload-ID"] == "api-gateway"
        assert request.headers["X-Internal-Tenant-ID"] == "tenant-1"
        assert request.headers["X-Correlation-ID"] == "correlation-1"
        assert request.headers["Idempotency-Key"] == "idem-1"
        return httpx.Response(201, json=_match_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MatchHttpClient(
            http_client=http_client,
            base_url="https://matches.test",
            authenticator=LocalHeaderAuthenticator(),
        )
        match = await client.create_match(
            scenario_id="scn_sql_injection_login",
            scenario_version="1.0.0",
            idempotency_key="idem-1",
            context=CONTEXT,
        )

    assert match.id == "match_123"
    assert match.scenario.snapshot_id == "ssnap_sql_login_1_0_0"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (404, NotFoundError),
        (409, ConflictError),
        (500, ServiceUnavailableError),
    ],
)
async def test_match_client_maps_downstream_statuses(
    status_code: int,
    expected: type[Exception],
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status_code, json={}))
    ) as http_client:
        client = MatchHttpClient(
            http_client=http_client,
            base_url="https://matches.test",
            authenticator=LocalHeaderAuthenticator(),
        )
        with pytest.raises(expected):
            await client.get_match(match_id="match_123", context=CONTEXT)


@pytest.mark.anyio
async def test_match_client_rejects_malformed_response() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"id": "bad"}))
    ) as http_client:
        client = MatchHttpClient(
            http_client=http_client,
            base_url="https://matches.test",
            authenticator=LocalHeaderAuthenticator(),
        )
        with pytest.raises(BadGatewayError):
            await client.get_match(match_id="match_123", context=CONTEXT)


@pytest.mark.anyio
async def test_match_client_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("late", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MatchHttpClient(
            http_client=http_client,
            base_url="https://matches.test",
            authenticator=LocalHeaderAuthenticator(),
        )
        with pytest.raises(GatewayTimeoutError):
            await client.get_match(match_id="match_123", context=CONTEXT)
