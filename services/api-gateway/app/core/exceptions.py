from collections.abc import Sequence
from typing import Any


class GatewayError(Exception):
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


class UnauthorizedError(GatewayError):
    def __init__(self, message: str = "Authentication is required or invalid.") -> None:
        super().__init__(status_code=401, code="unauthorized", message=message)


class ForbiddenError(GatewayError):
    def __init__(self, message: str = "The caller lacks permission for this operation.") -> None:
        super().__init__(status_code=403, code="forbidden", message=message)


class BadGatewayError(GatewayError):
    def __init__(self) -> None:
        super().__init__(
            status_code=502,
            code="invalid_downstream_response",
            message="A required service returned an invalid response.",
        )


class ServiceUnavailableError(GatewayError):
    def __init__(
        self,
        message: str = "The requested operation is temporarily unavailable.",
    ) -> None:
        super().__init__(status_code=503, code="downstream_unavailable", message=message)


class GatewayTimeoutError(GatewayError):
    def __init__(self) -> None:
        super().__init__(
            status_code=504,
            code="downstream_timeout",
            message="A required service did not respond in time.",
        )
