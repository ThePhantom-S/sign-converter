from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.common import ErrorResponse

logger = get_logger(__name__)


class AppError(Exception):
    """Base application error with structured API response fields."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def _build_error_response(
    *,
    message: str,
    error_code: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        message=message,
        error_code=error_code,
        details=details or {},
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "app_error",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
    )
    return _build_error_response(
        message=exc.message,
        error_code=exc.error_code,
        status_code=exc.status_code,
        details=exc.details,
    )


async def http_exception_handler(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    error_code = f"HTTP_{exc.status_code}"
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details: dict[str, Any] = {}
    if isinstance(exc.detail, dict):
        message = str(exc.detail.get("message", message))
        details = exc.detail

    return _build_error_response(
        message=message,
        error_code=error_code,
        status_code=exc.status_code,
        details=details,
    )


async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _build_error_response(
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": exc.errors()},
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return _build_error_response(
        message="An unexpected error occurred",
        error_code="INTERNAL_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
