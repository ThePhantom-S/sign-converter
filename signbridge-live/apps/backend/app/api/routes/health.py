from fastapi import APIRouter

from app.schemas.common import SuccessResponse
from app.schemas.health import HealthResponse, LivenessResponse
from app.services.health import build_health_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Lightweight liveness probe for load balancers."""
    return LivenessResponse()


@router.get("/health/detailed", response_model=SuccessResponse[HealthResponse])
async def readiness() -> SuccessResponse[HealthResponse]:
    """Detailed readiness check including Supabase."""
    health = await build_health_response()
    return SuccessResponse(data=health)
