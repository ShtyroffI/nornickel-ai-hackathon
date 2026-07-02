from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.sql.user import User
from app.schemas.query import QueryRequest, QueryResponse
from app.services.search.service import SearchFilters, SearchService


router = APIRouter()
search_service = SearchService()


@router.post("", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    _user: Annotated[User, Depends(get_current_user)],
) -> QueryResponse:
    filters = SearchFilters(
        geography=payload.geography,
        year_from=payload.year_from,
        year_to=payload.year_to,
        min_confidence=payload.min_confidence,
        depth=payload.depth,
    )
    result = search_service.search(payload.text, filters)
    return QueryResponse(
        text=payload.text,
        sources=result.get("results", []),
        consensus=[],
        disagreements=[],
        confidence=0.0,
        gaps=[],
    )
