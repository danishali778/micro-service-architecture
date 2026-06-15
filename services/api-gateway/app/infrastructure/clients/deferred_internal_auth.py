from app.core.exceptions import ServiceUnavailableError
from app.domain.value_objects.tenant_context import TrustedRequestContext


class DeferredInternalAuthenticator:
    def headers(self, context: TrustedRequestContext) -> dict[str, str]:
        del context
        raise ServiceUnavailableError("Internal workload authentication is not configured.")
