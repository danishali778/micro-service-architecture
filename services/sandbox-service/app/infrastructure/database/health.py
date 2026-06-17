from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.application.ports.provider import SandboxProvider
from app.core.config import Settings
from app.infrastructure.database.migrations import CURRENT_MIGRATION_REVISION
from app.security.internal_auth import InternalAuthValidator


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    ready: bool
    code: str = "ok"
    message: str = "ok"


class ReadinessChecker(Protocol):
    def check(self) -> ReadinessResult: ...


class StaticReadinessChecker:
    def __init__(self, ready: bool = True, code: str = "service_unavailable") -> None:
        self._ready = ready
        self._code = code

    def check(self) -> ReadinessResult:
        if self._ready:
            return ReadinessResult(ready=True)
        return ReadinessResult(
            ready=False,
            code=self._code,
            message="The service is not ready.",
        )


class DatabaseReadinessChecker:
    def __init__(
        self,
        *,
        engine: Engine,
        settings: Settings,
        internal_auth_validator: InternalAuthValidator,
        provider: SandboxProvider,
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._internal_auth_validator = internal_auth_validator
        self._provider = provider

    def check(self) -> ReadinessResult:
        if not self._internal_auth_validator.is_ready or not self._provider.is_ready:
            return ReadinessResult(
                ready=False,
                code="provider_or_auth_unconfigured",
                message="Sandbox provider or internal authentication is not configured.",
            )

        version: str | None = None
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                if self._settings.require_current_migration:
                    version = connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalar_one_or_none()
        except SQLAlchemyError:
            return ReadinessResult(
                ready=False,
                code="database_unavailable",
                message="The sandbox database is unavailable.",
            )

        if self._settings.require_current_migration and version != CURRENT_MIGRATION_REVISION:
            return ReadinessResult(
                ready=False,
                code="migration_not_current",
                message="The sandbox database migration is not current.",
            )
        return ReadinessResult(ready=True)
