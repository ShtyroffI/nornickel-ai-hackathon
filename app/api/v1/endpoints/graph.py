from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.neo4j.driver import Neo4jDriver, get_neo4j
from app.models.sql.user import User
from app.schemas.graph import EntityCreate, EntityOut, GraphSubgraph, RelationCreate
from app.services.graph.service import GraphService


router = APIRouter()


def get_graph_service(driver: Annotated[Neo4jDriver, Depends(get_neo4j)]) -> GraphService:
    return GraphService(driver)


@router.post("/entities", response_model=EntityOut)
def create_entity(
    payload: EntityCreate,
    service: Annotated[GraphService, Depends(get_graph_service)],
    _user: Annotated[User, Depends(get_current_user)],
) -> EntityOut:
    eid = service.upsert_entity(payload)
    return EntityOut(id=eid, **payload.model_dump())


@router.post("/relations", status_code=204)
def create_relation(
    payload: RelationCreate,
    service: Annotated[GraphService, Depends(get_graph_service)],
    _user: Annotated[User, Depends(get_current_user)],
) -> None:
    service.create_relation(payload)


@router.get("/entities/{entity_id}/neighborhood", response_model=GraphSubgraph)
def neighborhood(
    entity_id: str,
    depth: int = 3,
    service: Annotated[GraphService, Depends(get_graph_service)] = None,
    _user: Annotated[User, Depends(get_current_user)] = None,
) -> GraphSubgraph:
    raw = service.neighborhood(entity_id, depth=depth)
    nodes = [
        EntityOut(
            id=item["m"].get("id", ""),
            type=next((l for l in item["m"].labels if l != "Resource"), "Entity"),
            name=item["m"].get("name", ""),
            properties={k: v for k, v in item["m"].items() if k not in {"id", "name"}},
        )
        for item in raw
    ]
    edges = [dict(rel) for item in raw for rel in item.get("rels", [])]
    return GraphSubgraph(nodes=nodes, edges=edges)
