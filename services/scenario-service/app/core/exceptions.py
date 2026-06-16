from collections.abc import Sequence
from typing import Any


class ScenarioServiceError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Sequence[dict[str, Any]] = (),
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = list(details)


class UnauthorizedError(ScenarioServiceError):
    def __init__(self, message: str = "Internal authentication is required or invalid.") -> None:
        super().__init__(status_code=401, code="unauthorized", message=message)


class ForbiddenError(ScenarioServiceError):
    def __init__(self, message: str = "The caller lacks permission for this operation.") -> None:
        super().__init__(status_code=403, code="forbidden", message=message)


class ValidationFailedError(ScenarioServiceError):
    def __init__(
        self,
        message: str = "The request contains invalid fields.",
        *,
        details: Sequence[dict[str, Any]] = (),
    ) -> None:
        super().__init__(
            status_code=422,
            code="validation_error",
            message=message,
            details=details,
        )


class ServiceUnavailableError(ScenarioServiceError):
    def __init__(
        self,
        message: str = "The requested operation is temporarily unavailable.",
        *,
        code: str = "service_unavailable",
    ) -> None:
        super().__init__(status_code=503, code=code, message=message)
