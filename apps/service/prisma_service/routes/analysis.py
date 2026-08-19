"""Analytics endpoints kept thin and free of mathematical formulas."""

from fastapi import APIRouter, HTTPException

from prisma.analytics import AnalyticsValidationError

from ..demo import make_demo_request
from ..models import CompareAnalysisRequest
from ..services import compare_analysis


router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/compare")
def compare(request: CompareAnalysisRequest) -> dict:
    try:
        return compare_analysis(request)
    except (AnalyticsValidationError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/demo")
def demo() -> dict:
    return compare_analysis(make_demo_request())
