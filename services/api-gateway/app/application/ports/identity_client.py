from typing import Protocol

from app.domain.auth import AuthTokenResponse
from app.domain.value_objects.tenant_context import Principal


class IdentityClient(Protocol):
    async def login(
        self,
        *,
        email: str,
        password: str,
        tenant_id: str,
        correlation_id: str,
    ) -> AuthTokenResponse: ...

    async def refresh(
        self,
        *,
        refresh_token: str,
        correlation_id: str,
    ) -> AuthTokenResponse: ...

    async def logout(self, *, access_token: str, correlation_id: str) -> None: ...

    async def resolve_session_context(
        self,
        *,
        subject_id: str,
        session_id: str,
        correlation_id: str,
    ) -> Principal: ...
