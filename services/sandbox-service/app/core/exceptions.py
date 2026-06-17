from collections.abc import Sequence
from typing import Any


class SandboxServiceError(Exception):
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


class UnauthorizedError(SandboxServiceError):
    def __init__(self, message: str = "Internal authentication is required or invalid.") -> None:
        super().__init__(status_code=401, code="unauthorized", message=message)


class ForbiddenError(SandboxServiceError):
    def __init__(self, message: str = "The caller lacks permission for this operation.") -> None:
        super().__init__(status_code=403, code="forbidden", message=message)


class NotFoundError(SandboxServiceError):
    def __init__(
        self,
        message: str = "The requested sandbox was not found.",
        *,
        code: str = "sandbox_not_found",
    ) -> None:
        super().__init__(status_code=404, code=code, message=message)


class ConflictError(SandboxServiceError):
    def __init__(
        self,
        message: str = "The requested operation conflicts with current state.",
    ) -> None:
        super().__init__(status_code=409, code="conflict", message=message)


class ValidationFailedError(SandboxServiceError):
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


class BadGatewayError(SandboxServiceError):
    def __init__(self) -> None:
        super().__init__(
            status_code=502,
            code="invalid_provider_response",
            message="A required provider returned an invalid response.",
        )


class ServiceUnavailableError(SandboxServiceError):
    def __init__(
        self,
        message: str = "The requested operation is temporarily unavailable.",
        *,
        code: str = "service_unavailable",
    ) -> None:
        super().__init__(status_code=503, code=code, message=message)


class GatewayTimeoutError(SandboxServiceError):
    def __init__(self) -> None:
        super().__init__(
            status_code=504,
            code="provider_timeout",
            message="A required provider did not respond in time.",
        )
