from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.sql.user import User
from app.schemas.review import ReviewRequest, ReviewResponse
from app.services.analytics.service import AnalyticsService


router = APIRouter()
analytics = AnalyticsService()


@router.post("", response_model=ReviewResponse)
def review(
    payload: ReviewRequest,
    _user: Annotated[User, Depends(get_current_user)],
) -> ReviewResponse:
    result = analytics.generate_review(payload.topic, payload.group_by)
    return ReviewResponse(
        topic=result["topic"],
        summary=result.get("summary", ""),
        consensus=result["consensus"],
        disagreements=result["disagreements"],
        sources=result["sources"],
        sources_count=result["sources_count"],
        confidence=result["confidence"],
    )
