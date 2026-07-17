from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.config import get_settings


class ServiceStatus(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"
    DEGRADED = "degraded"


class DependencyHealth(BaseModel):
    name: str
    status: ServiceStatus
    message: str | None = None
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    status: ServiceStatus
    service: str = Field(default_factory=lambda: get_settings().APP_NAME)
    version: str = Field(default_factory=lambda: get_settings().APP_VERSION)
    environment: str = Field(default_factory=lambda: get_settings().ENVIRONMENT)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dependencies: list[DependencyHealth] = Field(default_factory=list)


class LivenessResponse(BaseModel):
    status: str = "ok"
