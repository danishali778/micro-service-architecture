from app.domain.value_objects.tenant_context import TrustedRequestContext


class LocalHeaderAuthenticator:
    """Local-only stand-in for a future authenticated workload identity mechanism."""

    def headers(self, context: TrustedRequestContext) -> dict[str, str]:
        return {
            "X-Internal-Auth-Mode": "local",
            "X-Internal-Workload-ID": "api-gateway",
            "X-Internal-Subject-ID": context.principal.subject_id,
            "X-Internal-Tenant-ID": context.principal.tenant_id,
            "X-Internal-Scopes": " ".join(sorted(context.principal.scopes)),
            "X-Correlation-ID": context.correlation_id,
        }
