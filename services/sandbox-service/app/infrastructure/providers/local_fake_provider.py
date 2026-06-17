from app.domain.entities.sandbox import CleanupResult, ProviderAllocation


class LocalFakeSandboxProvider:
    name = "local_fake"
    is_ready = True

    def provision(self, *, sandbox_id: str, match_id: str) -> ProviderAllocation:
        return ProviderAllocation(
            allocation_id=f"local_{sandbox_id}",
            metadata={
                "match_id": match_id,
                "endpoint": "http://sandbox.local/target",
            },
        )

    def terminate(self, *, allocation: dict[str, object]) -> CleanupResult:
        return CleanupResult(status="completed", details=[])
