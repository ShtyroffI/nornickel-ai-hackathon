from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    geography: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    depth: int = Field(default=3, ge=1, le=4)


class QueryResponse(BaseModel):
    text: str
    sources: list[dict] = []
    subgraph: dict | None = None
    consensus: list[str] = []
    disagreements: list[str] = []
    confidence: float = 0.0
    gaps: list[str] = []
