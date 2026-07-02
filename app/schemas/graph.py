from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    MATERIAL = "Material"
    PROCESS = "Process"
    EQUIPMENT = "Equipment"
    PROPERTY = "Property"
    EXPERIMENT = "Experiment"
    PUBLICATION = "Publication"
    EXPERT = "Expert"
    FACILITY = "Facility"


class RelationType(str, Enum):
    USES_MATERIAL = "uses_material"
    OPERATES_AT_CONDITION = "operates_at_condition"
    PRODUCES_OUTPUT = "produces_output"
    DESCRIBED_IN = "described_in"
    VALIDATED_BY = "validated_by"
    CONTRADICTS = "contradicts"


class EntityCreate(BaseModel):
    type: EntityType
    name: str
    properties: dict = Field(default_factory=dict)
    source: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EntityOut(EntityCreate):
    id: str


class RelationCreate(BaseModel):
    source_id: str
    target_id: str
    type: RelationType
    properties: dict = Field(default_factory=dict)
    source: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class GraphSubgraph(BaseModel):
    nodes: list[EntityOut]
    edges: list[dict]
