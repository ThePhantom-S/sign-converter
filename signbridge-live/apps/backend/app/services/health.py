import time

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.supabase import supabase_manager
from app.schemas.health import DependencyHealth, HealthResponse, ServiceStatus

logger = get_logger(__name__)


async def _check_supabase() -> DependencyHealth:
    settings = get_settings()
    if not settings.SUPABASE_ENABLED:
        return DependencyHealth(name="supabase", status=ServiceStatus.DISABLED)

    if not settings.supabase_configured:
        return DependencyHealth(
            name="supabase",
            status=ServiceStatus.DEGRADED,
            message="Supabase credentials are not configured",
        )

    start = time.perf_counter()
    try:
        healthy = await supabase_manager.ping()
        latency_ms = (time.perf_counter() - start) * 1000
        if healthy:
            return DependencyHealth(
                name="supabase",
                status=ServiceStatus.HEALTHY,
                latency_ms=round(latency_ms, 2),
            )
        return DependencyHealth(
            name="supabase",
            status=ServiceStatus.UNHEALTHY,
            message="Supabase client is not connected",
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.warning("supabase_health_check_failed", error=str(exc))
        return DependencyHealth(
            name="supabase",
            status=ServiceStatus.UNHEALTHY,
            message="Supabase connection failed",
            latency_ms=round(latency_ms, 2),
        )


def _aggregate_status(dependencies: list[DependencyHealth]) -> ServiceStatus:
    active = [
        dependency
        for dependency in dependencies
        if dependency.status not in (ServiceStatus.DISABLED, ServiceStatus.DEGRADED)
    ]
    if not active:
        return ServiceStatus.HEALTHY

    if any(dependency.status == ServiceStatus.UNHEALTHY for dependency in active):
        return ServiceStatus.UNHEALTHY

    if any(dependency.status == ServiceStatus.DEGRADED for dependency in dependencies):
        return ServiceStatus.DEGRADED

    return ServiceStatus.HEALTHY


async def build_health_response() -> HealthResponse:
    dependencies = [await _check_supabase()]
    return HealthResponse(
        status=_aggregate_status(dependencies),
        dependencies=dependencies,
    )
