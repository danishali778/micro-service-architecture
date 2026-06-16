import httpx
import pytest
from app.core.exceptions import BadGatewayError, GatewayTimeoutError, ServiceUnavailableError
from app.domain.value_objects.tenant_context import Principal, TrustedRequestContext
from app.infrastructure.clients.local_internal_auth import LocalHeaderAuthenticator
from app.infrastructure.clients.scenario_http_client import ScenarioHttpClient

CONTEXT = TrustedRequestContext(
    principal=Principal(
        subject_id="subject-1",
        tenant_id="tenant-1",
        scopes=frozenset({"scenarios:read"}),
    ),
    correlation_id="correlation-1",
)


@pytest.mark.anyio
async def test_scenario_client_validates_response_and_propagates_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/v1/scenarios"
        assert request.headers["X-Internal-Tenant-ID"] == "tenant-1"
        assert request.headers["X-Correlation-ID"] == "correlation-1"
        assert request.url.params["limit"] == "25"
        assert request.url.params["cursor"] == "opaque"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "scn_sql_injection_login",
                        "latest_version": "1.0.0",
                        "title": "SQL Injection Login Bypass",
                        "summary": "Find and exploit an injectable login form.",
                        "difficulty": "beginner",
                        "category": "web-security",
                        "tags": ["sql-injection", "authentication"],
                        "estimated_duration_minutes": 30,
                        "status": "published",
                    }
                ],
                "next_cursor": None,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ScenarioHttpClient(
            http_client=http_client,
            base_url="https://scenario.test",
            authenticator=LocalHeaderAuthenticator(),
        )
        page = await client.list_scenarios(limit=25, cursor="opaque", context=CONTEXT)

    assert page.items[0].id == "scn_sql_injection_login"
    assert page.items[0].tags == ("sql-injection", "authentication")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (httpx.ReadTimeout("late"), GatewayTimeoutError),
        (httpx.ConnectError("offline"), ServiceUnavailableError),
    ],
)
async def test_scenario_client_maps_transport_failures(
    error: httpx.RequestError,
    expected: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        error.request = request
        raise error

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ScenarioHttpClient(
            http_client=http_client,
            base_url="https://scenario.test",
            authenticator=LocalHeaderAuthenticator(),
        )
        with pytest.raises(expected):
            await client.list_scenarios(limit=50, cursor=None, context=CONTEXT)


@pytest.mark.anyio
async def test_scenario_client_rejects_malformed_response() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"items": []}))
    ) as http_client:
        client = ScenarioHttpClient(
            http_client=http_client,
            base_url="https://scenario.test",
            authenticator=LocalHeaderAuthenticator(),
        )
        with pytest.raises(BadGatewayError):
            await client.list_scenarios(limit=50, cursor=None, context=CONTEXT)
