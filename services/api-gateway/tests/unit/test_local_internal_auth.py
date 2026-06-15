from app.domain.value_objects.tenant_context import Principal, TrustedRequestContext
from app.infrastructure.clients.local_internal_auth import LocalHeaderAuthenticator


def test_builds_local_trusted_context_headers() -> None:
    context = TrustedRequestContext(
        principal=Principal(
            subject_id="subject-1",
            tenant_id="tenant-1",
            scopes=frozenset({"scenarios:read", "matches:read"}),
        ),
        correlation_id="correlation-1",
    )

    headers = LocalHeaderAuthenticator().headers(context)

    assert headers["X-Internal-Workload-ID"] == "api-gateway"
    assert headers["X-Internal-Tenant-ID"] == "tenant-1"
    assert headers["X-Internal-Scopes"] == "matches:read scenarios:read"
    assert headers["X-Correlation-ID"] == "correlation-1"
