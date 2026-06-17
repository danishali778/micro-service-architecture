from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import SandboxServiceError

logger = structlog.get_logger(__name__)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SandboxServiceError)
    async def sandbox_error_handler(
        request: Request,
        exc: SandboxServiceError,
    ) -> JSONResponse:
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            correlation_id=_correlation_id(request),
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {"loc": [str(part) for part in error["loc"]], "msg": str(error["msg"])}
            for error in exc.errors()
        ]
        return _error_response(
            status_code=422,
            code="validation_error",
            message="The request contains invalid fields.",
            correlation_id=_correlation_id(request),
            details=details,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = _correlation_id(request)
        logger.exception("unhandled_sandbox_error", correlation_id=correlation_id, exc_info=exc)
        return _error_response(
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
            correlation_id=correlation_id,
            details=[],
        )


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", "unavailable"))


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    correlation_id: str,
    details: list[dict[str, Any]],
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation_id,
                "details": details,
            }
        },
    )
