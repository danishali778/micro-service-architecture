from typing import Protocol

from app.domain.entities.sandbox import CleanupResult, ProviderAllocation


class SandboxProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def is_ready(self) -> bool: ...

    def provision(self, *, sandbox_id: str, match_id: str) -> ProviderAllocation: ...

    def terminate(self, *, allocation: dict[str, object]) -> CleanupResult: ...
