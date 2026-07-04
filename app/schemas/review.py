from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    topic: str
    geography: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    group_by: list[str] = Field(default_factory=lambda: ["method", "year", "geography"])


class ReviewResponse(BaseModel):
    topic: str
    summary: str
    consensus: list[str]
    disagreements: list[str]
    groups: dict[str, list[str]]
    sources_count: int
    confidence: float
