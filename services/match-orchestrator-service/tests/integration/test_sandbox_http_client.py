import httpx
import pytest
from app.core.exceptions import (
    BadGatewayError,
    ConflictError,
    GatewayTimeoutError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.infrastructure.clients.sandbox_http_client import SandboxHttpClient
from app.security.internal_auth import TrustedInternalContext
from conftest import sample_snapshot

CONTEXT = TrustedInternalContext(
    workload_id="api-gateway",
    subject_id="subject-1",
    tenant_id="tenant-1",
    scopes=frozenset({"matches:create"}),
    correlation_id="correlation-1",
)


def _sandbox_payload() -> dict[str, object]:
    return {
        "id": "sandbox_123",
        "tenant_id": "tenant-1",
        "subject_id": "subject-1",
        "match_id": "match_123",
        "scenario": {
            "snapshot_id": "ssnap_sql_login_1_0_0",
            "scenario_id": "scn_sql_injection_login",
            "version": "1.0.0",
            "title": "SQL Injection Login Bypass",
        },
        "state": "ready",
        "status_reason": "local_provider_ready",
        "provider": "local_fake",
        "allocation": {"allocation_id": "local_sandbox_123"},
        "lease_expires_at": "2026-06-17T12:45:00+00:00",
        "created_at": "2026-06-17T12:00:00+00:00",
        "updated_at": "2026-06-17T12:00:01+00:00",
        "ready_at": "2026-06-17T12:00:01+00:00",
        "terminated_at": None,
        "failed_at": None,
        "cleanup": None,
    }


@pytest.mark.anyio
async def test_sandbox_client_provisions_with_internal_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/v1/sandboxes"
        assert request.headers["X-Internal-Workload-ID"] == "match-orchestrator-service"
        assert request.headers["X-Internal-Tenant-ID"] == "tenant-1"
        assert request.headers["X-Internal-Scopes"] == "sandboxes:provision"
        assert request.headers["X-Correlation-ID"] == "correlation-1"
        assert request.headers["Idempotency-Key"] == "idem-1"
        assert request.read()
        return httpx.Response(201, json=_sandbox_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SandboxHttpClient(http_client=http_client, base_url="https://sandbox.test")
        sandbox = await client.provision_sandbox(
            match_id="match_123",
            scenario=sample_snapshot(),
            idempotency_key="idem-1",
            context=CONTEXT,
        )

    assert sandbox.id == "sandbox_123"
    assert sandbox.state == "ready"
    assert sandbox.allocation["allocation_id"] == "local_sandbox_123"


@pytest.mark.anyio
async def test_sandbox_client_terminates_with_internal_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/v1/sandboxes/sandbox_123/terminate"
        assert request.headers["X-Internal-Scopes"] == "sandboxes:terminate"
        assert request.headers["Idempotency-Key"] == "term-1"
        return httpx.Response(200, json={**_sandbox_payload(), "state": "terminated"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SandboxHttpClient(http_client=http_client, base_url="https://sandbox.test")
        sandbox = await client.terminate_sandbox(
            sandbox_id="sandbox_123",
            reason="match_cancelled",
            idempotency_key="term-1",
            context=CONTEXT,
        )

    assert sandbox.state == "terminated"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (404, NotFoundError),
        (409, ConflictError),
        (500, ServiceUnavailableError),
    ],
)
async def test_sandbox_client_maps_downstream_statuses(
    status_code: int,
    expected: type[Exception],
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status_code, json={}))
    ) as http_client:
        client = SandboxHttpClient(http_client=http_client, base_url="https://sandbox.test")
        with pytest.raises(expected):
            await client.terminate_sandbox(
                sandbox_id="sandbox_123",
                reason="match_cancelled",
                idempotency_key="term-1",
                context=CONTEXT,
            )


@pytest.mark.anyio
async def test_sandbox_client_rejects_malformed_response() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"id": "bad"}))
    ) as http_client:
        client = SandboxHttpClient(http_client=http_client, base_url="https://sandbox.test")
        with pytest.raises(BadGatewayError):
            await client.terminate_sandbox(
                sandbox_id="sandbox_123",
                reason="match_cancelled",
                idempotency_key="term-1",
                context=CONTEXT,
            )


@pytest.mark.anyio
async def test_sandbox_client_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("late", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SandboxHttpClient(http_client=http_client, base_url="https://sandbox.test")
        with pytest.raises(GatewayTimeoutError):
            await client.provision_sandbox(
                match_id="match_123",
                scenario=sample_snapshot(),
                idempotency_key="idem-1",
                context=CONTEXT,
            )
