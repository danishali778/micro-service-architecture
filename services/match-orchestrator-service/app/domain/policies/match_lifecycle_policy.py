from app.core.exceptions import ConflictError

ACTIVE_CANCELLABLE_STATES = frozenset({"created", "waiting_for_sandbox", "cancelling"})
TERMINAL_STATES = frozenset({"cancelled", "failed", "completed"})


def ensure_cancellable(state: str) -> None:
    if state in ACTIVE_CANCELLABLE_STATES or state in TERMINAL_STATES:
        return
    raise ConflictError("The match cannot be cancelled from its current state.")
