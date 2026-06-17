from app.core.exceptions import ConflictError

TERMINAL_STATES = frozenset({"terminated", "provision_failed", "cleanup_failed"})
TERMINATABLE_STATES = frozenset(
    {
        "ready",
        "expired",
        "termination_requested",
        "terminating",
        "terminated",
    }
)


def ensure_terminatable(state: str) -> None:
    if state in TERMINATABLE_STATES:
        return
    raise ConflictError("The sandbox cannot be terminated from its current state.")
