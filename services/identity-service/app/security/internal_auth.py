from dataclasses import dataclass

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, ServiceUnavailableError, UnauthorizedError


@dataclass(frozen=True, slots=True)
class TrustedInternalContext:
    workload_id: str
    correlation_id: str


class InternalAuthValidator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_ready(self) -> bool:
        return self._settings.internal_auth_mode == "local_header"

    def authenticate(self, request: Request) -> TrustedInternalContext:
        if self._settings.internal_auth_mode == "deferred":
            raise ServiceUnavailableError(
                "Internal workload authentication is not configured.",
                code="internal_auth_unconfigured",
            )

        if request.headers.get("X-Internal-Auth-Mode") != "local":
            raise UnauthorizedError()

        workload_id = request.headers.get("X-Internal-Workload-ID")
        correlation_id = getattr(request.state, "correlation_id", "unavailable")

        if not workload_id:
            raise UnauthorizedError()

        return TrustedInternalContext(
            workload_id=workload_id,
            correlation_id=correlation_id,
        )


def require_gateway(context: TrustedInternalContext) -> None:
    if context.workload_id != "api-gateway":
        raise ForbiddenError()


def require_admin_tooling(context: TrustedInternalContext) -> None:
    if context.workload_id not in {"admin-tooling", "local-seed"}:
        raise ForbiddenError()
