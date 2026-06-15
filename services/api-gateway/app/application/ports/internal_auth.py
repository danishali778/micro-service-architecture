from typing import Protocol

from app.domain.value_objects.tenant_context import TrustedRequestContext


class InternalAuthenticator(Protocol):
    def headers(self, context: TrustedRequestContext) -> dict[str, str]: ...
