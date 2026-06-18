from dataclasses import dataclass

from starlette.requests import Request

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, AuthorizationError


@dataclass(frozen=True, slots=True)
class TrustedInternalContext:
    workload_id: str
    subject_id: str
    tenant_id: str
    scopes: frozenset[str]
    correlation_id: str

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise AuthorizationError()


class InternalAuthValidator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_ready(self) -> bool:
        return self._settings.internal_auth_mode == "local_header"

    def validate(self, request: Request, *, required_workload: str) -> TrustedInternalContext:
        if self._settings.internal_auth_mode == "deferred":
            raise AuthenticationError(
                "Internal workload authentication is not configured.",
                code="internal_auth_unconfigured",
            )

        if request.headers.get("X-Internal-Auth-Mode") != "local":
            raise AuthenticationError()
        workload_id = _required_header(request, "X-Internal-Workload-ID")
        if workload_id != required_workload:
            raise AuthorizationError(code="wrong_workload")
        subject_id = _required_header(request, "X-Internal-Subject-ID")
        tenant_id = _required_header(request, "X-Internal-Tenant-ID")
        scopes = frozenset(_required_header(request, "X-Internal-Scopes").split())
        correlation_id = str(getattr(request.state, "correlation_id", "unavailable"))
        return TrustedInternalContext(
            workload_id=workload_id,
            subject_id=subject_id,
            tenant_id=tenant_id,
            scopes=scopes,
            correlation_id=correlation_id,
        )


def _required_header(request: Request, name: str) -> str:
    value = request.headers.get(name)
    if value is None or value.strip() == "":
        raise AuthenticationError()
    return value.strip()
