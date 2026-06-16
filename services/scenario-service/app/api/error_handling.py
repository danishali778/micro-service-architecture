from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import ScenarioServiceError

logger = structlog.get_logger()


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unavailable")


def _response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": _correlation_id(request),
                "details": details or [],
            }
        },
    )


async def unexpected_error_response(request: Request, error: Exception) -> JSONResponse:
    await logger.aexception(
        "unhandled_request_error",
        correlation_id=_correlation_id(request),
        error_type=type(error).__name__,
    )
    return _response(
        request=request,
        status_code=500,
        code="internal_error",
        message="An unexpected error occurred.",
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ScenarioServiceError)
    async def service_error_handler(
        request: Request,
        error: ScenarioServiceError,
    ) -> JSONResponse:
        return _response(
            request=request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            details=error.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]
        return _response(
            request=request,
            status_code=422,
            code="validation_error",
            message="The request contains invalid fields.",
            details=details,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
        return await unexpected_error_response(request, error)
