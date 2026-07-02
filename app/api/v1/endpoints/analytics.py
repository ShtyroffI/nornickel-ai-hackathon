from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.sql.user import User
from app.services.analytics.service import AnalyticsService


router = APIRouter()
analytics = AnalyticsService()


class GapsRequest(BaseModel):
    materials: list[str]
    processes: list[str]
    conditions: list[str]


class CompareRequest(BaseModel):
    variant_a: str
    variant_b: str
    criteria: list[str]


@router.get("/recommend")
def recommend(topic: str, _user: Annotated[User, Depends(get_current_user)]) -> dict:
    return analytics.recommend(topic)


@router.post("/gaps")
def gaps(payload: GapsRequest, _user: Annotated[User, Depends(get_current_user)]) -> list[dict]:
    return analytics.find_gaps(payload.materials, payload.processes, payload.conditions)


@router.post("/compare")
def compare(payload: CompareRequest, _user: Annotated[User, Depends(get_current_user)]) -> dict:
    return analytics.compare(payload.variant_a, payload.variant_b, payload.criteria)
