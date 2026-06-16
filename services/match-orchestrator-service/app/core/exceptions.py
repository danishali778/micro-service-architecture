from collections.abc import Sequence
from typing import Any


class MatchServiceError(Exception):
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


class UnauthorizedError(MatchServiceError):
    def __init__(self, message: str = "Internal authentication is required or invalid.") -> None:
        super().__init__(status_code=401, code="unauthorized", message=message)


class ForbiddenError(MatchServiceError):
    def __init__(self, message: str = "The caller lacks permission for this operation.") -> None:
        super().__init__(status_code=403, code="forbidden", message=message)


class NotFoundError(MatchServiceError):
    def __init__(
        self,
        message: str = "The requested resource was not found.",
        *,
        code: str = "not_found",
    ) -> None:
        super().__init__(status_code=404, code=code, message=message)


class ConflictError(MatchServiceError):
    def __init__(
        self,
        message: str = "The requested operation conflicts with current state.",
    ) -> None:
        super().__init__(status_code=409, code="conflict", message=message)


class ValidationFailedError(MatchServiceError):
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


class BadGatewayError(MatchServiceError):
    def __init__(self) -> None:
        super().__init__(
            status_code=502,
            code="invalid_downstream_response",
            message="A required service returned an invalid response.",
        )


class ServiceUnavailableError(MatchServiceError):
    def __init__(
        self,
        message: str = "The requested operation is temporarily unavailable.",
        *,
        code: str = "service_unavailable",
    ) -> None:
        super().__init__(status_code=503, code=code, message=message)


class GatewayTimeoutError(MatchServiceError):
    def __init__(self) -> None:
        super().__init__(
            status_code=504,
            code="downstream_timeout",
            message="A required service did not respond in time.",
        )
