from collections.abc import Sequence
from typing import Any


class IdentityServiceError(Exception):
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


class InvalidCredentialsError(IdentityServiceError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="invalid_credentials",
            message="Authentication failed.",
        )


class UnauthorizedError(IdentityServiceError):
    def __init__(self, message: str = "Internal authentication is required or invalid.") -> None:
        super().__init__(status_code=401, code="unauthorized", message=message)


class ForbiddenError(IdentityServiceError):
    def __init__(self, message: str = "The caller lacks permission for this operation.") -> None:
        super().__init__(status_code=403, code="forbidden", message=message)


class NotFoundError(IdentityServiceError):
    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(status_code=404, code="not_found", message=message)


class ConflictError(IdentityServiceError):
    def __init__(self, message: str = "The requested change conflicts with current state.") -> None:
        super().__init__(status_code=409, code="conflict", message=message)


class ValidationFailedError(IdentityServiceError):
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


class ServiceUnavailableError(IdentityServiceError):
    def __init__(
        self,
        message: str = "The requested operation is temporarily unavailable.",
        *,
        code: str = "service_unavailable",
    ) -> None:
        super().__init__(status_code=503, code=code, message=message)


class UpstreamTimeoutError(IdentityServiceError):
    def __init__(self) -> None:
        super().__init__(
            status_code=504,
            code="upstream_timeout",
            message="A required identity provider did not respond in time.",
        )
