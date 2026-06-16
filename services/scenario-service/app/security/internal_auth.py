from dataclasses import dataclass

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, ServiceUnavailableError, UnauthorizedError


@dataclass(frozen=True, slots=True)
class TrustedInternalContext:
    workload_id: str
    subject_id: str
    tenant_id: str
    scopes: frozenset[str]
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
        subject_id = request.headers.get("X-Internal-Subject-ID")
        tenant_id = request.headers.get("X-Internal-Tenant-ID")
        raw_scopes = request.headers.get("X-Internal-Scopes")
        correlation_id = getattr(request.state, "correlation_id", "unavailable")

        if not workload_id or not subject_id or not tenant_id or raw_scopes is None:
            raise UnauthorizedError()

        scopes = frozenset(scope for scope in raw_scopes.split(" ") if scope)
        return TrustedInternalContext(
            workload_id=workload_id,
            subject_id=subject_id,
            tenant_id=tenant_id,
            scopes=scopes,
            correlation_id=correlation_id,
        )


def require_gateway_scenario_read(context: TrustedInternalContext) -> None:
    if context.workload_id != "api-gateway":
        raise ForbiddenError()
    if "scenarios:read" not in context.scopes:
        raise ForbiddenError()
