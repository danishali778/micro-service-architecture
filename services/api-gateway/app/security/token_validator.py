from typing import Protocol

from app.domain.value_objects.tenant_context import Principal


class TokenValidator(Protocol):
    @property
    def is_ready(self) -> bool: ...

    async def initialize(self) -> None: ...

    async def ensure_ready(self) -> bool: ...

    async def validate(self, token: str) -> Principal: ...
