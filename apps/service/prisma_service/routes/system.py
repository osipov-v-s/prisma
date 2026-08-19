"""Service readiness and version endpoints."""

from fastapi import APIRouter

from prisma.analytics import ALGORITHM_VERSION

from ..config import SERVICE_NAME, SERVICE_VERSION


router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "service_version": SERVICE_VERSION,
        "analytics_version": ALGORITHM_VERSION,
    }
