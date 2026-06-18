import httpx
import pytest
from app.core.exceptions import BadGatewayError, GatewayTimeoutError, ServiceUnavailableError
from app.domain.entities.match import SandboxProvision
from app.infrastructure.clients.red_agent_http_client import RedAgentHttpClient
from app.security.internal_auth import TrustedInternalContext
from conftest import sample_snapshot

CONTEXT = TrustedInternalContext(
    workload_id="api-gateway",
    subject_id="subject-1",
    tenant_id="tenant-1",
    scopes=frozenset({"matches:create"}),
    correlation_id="correlation-1",
)


def _red_run_payload() -> dict[str, object]:
    return {
        "id": "redrun_123",
        "tenant_id": "tenant-1",
        "subject_id": "subject-1",
        "match_id": "match_123",
        "sandbox_id": "sandbox_123",
        "scenario": {
            "snapshot_id": "ssnap_sql_login_1_0_0",
            "scenario_id": "scn_sql_injection_login",
            "version": "1.0.0",
            "title": "SQL Injection Login Bypass",
        },
        "state": "proposal_ready",
        "status_reason": "fake_agent_proposal_ready",
        "agent": {"adapter": "local_fake", "profile_ref": "red-agent-local-fake@1"},
        "proposal": {
            "proposal_id": "attackprop_123",
            "proposal_type": "http_request",
            "title": "Probe login form for SQL injection",
            "summary": "Submit a controlled authentication bypass payload.",
            "rationale": "The scenario target is a login bypass training target.",
            "action": {"kind": "http_request", "method": "POST", "path": "/login"},
            "expected_signal": "Authenticated response.",
            "risk_level": "training_safe",
            "confidence": 0.75,
        },
        "created_at": "2026-06-18T12:00:00+00:00",
        "updated_at": "2026-06-18T12:00:01+00:00",
        "completed_at": "2026-06-18T12:00:01+00:00",
        "failed_at": None,
    }


@pytest.mark.anyio
async def test_red_agent_client_starts_run_with_internal_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/v1/red-runs"
        assert request.headers["X-Internal-Workload-ID"] == "match-orchestrator-service"
        assert request.headers["X-Internal-Tenant-ID"] == "tenant-1"
        assert request.headers["X-Internal-Scopes"] == "red:runs:start"
        assert request.headers["X-Correlation-ID"] == "correlation-1"
        assert request.headers["Idempotency-Key"] == "idem-1"
        assert request.read()
        return httpx.Response(201, json=_red_run_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = RedAgentHttpClient(http_client=http_client, base_url="https://red-agent.test")
        red_run = await client.start_red_run(
            match_id="match_123",
            scenario=sample_snapshot(),
            sandbox=SandboxProvision(
                id="sandbox_123",
                state="ready",
                provider="local_fake",
                allocation={"allocation_id": "local_sandbox_123"},
            ),
            idempotency_key="idem-1",
            context=CONTEXT,
        )

    assert red_run.id == "redrun_123"
    assert red_run.state == "proposal_ready"
    assert red_run.proposal.id == "attackprop_123"


@pytest.mark.anyio
async def test_red_agent_client_rejects_malformed_response() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"id": "bad"}))
    ) as http_client:
        client = RedAgentHttpClient(http_client=http_client, base_url="https://red-agent.test")
        with pytest.raises(BadGatewayError):
            await client.start_red_run(
                match_id="match_123",
                scenario=sample_snapshot(),
                sandbox=SandboxProvision(
                    id="sandbox_123",
                    state="ready",
                    provider="local_fake",
                    allocation={"allocation_id": "local_sandbox_123"},
                ),
                idempotency_key="idem-1",
                context=CONTEXT,
            )


@pytest.mark.anyio
async def test_red_agent_client_maps_unavailable_and_timeout() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503, json={}))
    ) as http_client:
        client = RedAgentHttpClient(http_client=http_client, base_url="https://red-agent.test")
        with pytest.raises(ServiceUnavailableError):
            await client.start_red_run(
                match_id="match_123",
                scenario=sample_snapshot(),
                sandbox=SandboxProvision(
                    id="sandbox_123",
                    state="ready",
                    provider="local_fake",
                    allocation={"allocation_id": "local_sandbox_123"},
                ),
                idempotency_key="idem-1",
                context=CONTEXT,
            )

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("late", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as http_client:
        client = RedAgentHttpClient(http_client=http_client, base_url="https://red-agent.test")
        with pytest.raises(GatewayTimeoutError):
            await client.start_red_run(
                match_id="match_123",
                scenario=sample_snapshot(),
                sandbox=SandboxProvision(
                    id="sandbox_123",
                    state="ready",
                    provider="local_fake",
                    allocation={"allocation_id": "local_sandbox_123"},
                ),
                idempotency_key="idem-1",
                context=CONTEXT,
            )
