from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware.request_context import RequestContextMiddleware
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.supabase import supabase_manager
from app.cv.landmarks import close_hands
from app.schemas.health import LivenessResponse
from app.services.gesture import gesture_service
from app.utils.exceptions import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    logger.info(
        "application_starting",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
    )

    try:
        supabase_manager.connect()
    except Exception as exc:
        logger.warning("supabase_startup_failed", error=str(exc))

    # Load gesture recognition model (non-fatal if model file not found)
    try:
        gesture_service.load_model()
    except Exception as exc:
        logger.warning("gesture_model_load_failed", error=str(exc))

    yield

    supabase_manager.disconnect()
    close_hands()  # Release MediaPipe Hands instance
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_DEFAULT]
        if settings.RATE_LIMIT_ENABLED
        else [],
    )

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    application.add_exception_handler(Exception, unhandled_exception_handler)

    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    rate_limit = (
        settings.RATE_LIMIT_DEFAULT
        if settings.RATE_LIMIT_ENABLED
        else "1000/minute"
    )

    @application.get("/health", response_model=LivenessResponse, tags=["health"])
    @limiter.limit(rate_limit)
    async def root_health(request: Request) -> LivenessResponse:
        return LivenessResponse()

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return application


app = create_app()
