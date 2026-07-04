from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
import tempfile
import shutil
import os

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
    nodes_dict = {}
    edges_list = []
    
    for item in raw:
        if item.get("n"):
            n = item["n"]
            n_labels = item.get("n_labels", [])
            nid = n.get("id", "")
            if nid and nid not in nodes_dict:
                nodes_dict[nid] = EntityOut(
                    id=nid,
                    type=next((l for l in n_labels if l != "Resource"), "Entity"),
                    name=n.get("name", ""),
                    properties={k: v for k, v in n.items() if k not in {"id", "name"}},
                )
        if item.get("m"):
            m = item["m"]
            m_labels = item.get("m_labels", [])
            mid = m.get("id", "")
            if mid and mid not in nodes_dict:
                nodes_dict[mid] = EntityOut(
                    id=mid,
                    type=next((l for l in m_labels if l != "Resource"), "Entity"),
                    name=m.get("name", ""),
                    properties={k: v for k, v in m.items() if k not in {"id", "name"}},
                )
        for rel in item.get("rels") or []:
            edges_list.append({
                "source": rel.get("start", ""),
                "target": rel.get("end", ""),
                "type": rel.get("type", ""),
                "properties": rel.get("props", {})
            })
            
    return GraphSubgraph(nodes=list(nodes_dict.values()), edges=edges_list)


@router.get("/search", response_model=GraphSubgraph)
def search_graph(
    q: str,
    depth: int = 2,
    service: Annotated[GraphService, Depends(get_graph_service)] = None,
    _user: Annotated[User, Depends(get_current_user)] = None,
) -> GraphSubgraph:
    raw = service.search_neighborhood(q, depth=depth)
    nodes_dict = {}
    edges_list = []
    
    for item in raw:
        if item.get("n"):
            n = item["n"]
            n_labels = item.get("n_labels", [])
            nid = n.get("id", "")
            if nid and nid not in nodes_dict:
                nodes_dict[nid] = EntityOut(
                    id=nid,
                    type=next((l for l in n_labels if l != "Resource"), "Entity"),
                    name=n.get("name", ""),
                    properties={k: v for k, v in n.items() if k not in {"id", "name"}},
                )
        if item.get("m"):
            m = item["m"]
            m_labels = item.get("m_labels", [])
            mid = m.get("id", "")
            if mid and mid not in nodes_dict:
                nodes_dict[mid] = EntityOut(
                    id=mid,
                    type=next((l for l in m_labels if l != "Resource"), "Entity"),
                    name=m.get("name", ""),
                    properties={k: v for k, v in m.items() if k not in {"id", "name"}},
                )
        for rel in item.get("rels") or []:
            edges_list.append({
                "source": rel.get("start", ""),
                "target": rel.get("end", ""),
                "type": rel.get("type", ""),
                "properties": rel.get("props", {})
            })
            
    return GraphSubgraph(nodes=list(nodes_dict.values()), edges=edges_list)


@router.get("/stats")
def graph_stats(
    service: Annotated[GraphService, Depends(get_graph_service)],
    _user: Annotated[User, Depends(get_current_user)] = None,
) -> dict:
    # Query to count total nodes, total relationships, and list ingested publications
    cypher_stats = "MATCH (n) RETURN count(n) AS node_count"
    node_count = service.driver.run(cypher_stats)[0]["node_count"]
    
    cypher_rels = "MATCH ()-[r]->() RETURN count(r) AS rel_count"
    rel_count = service.driver.run(cypher_rels)[0]["rel_count"]
    
    cypher_pubs = "MATCH (n:Publication) RETURN n.name AS filename"
    pubs = [row["filename"] for row in service.driver.run(cypher_pubs)]
    
    return {
        "nodes_count": node_count,
        "relations_count": rel_count,
        "loaded_documents": pubs
    }

@router.post("/upload/estimate")
def estimate_upload(
    file: UploadFile = File(...),
    _user: Annotated[User, Depends(get_current_user)] = None,
) -> dict:
    from app.services.ingestion.service import IngestionService
    from app.services.nlp.service import extract_from_text
    
    # Save uploaded file to temp dir
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
        
    try:
        doc = IngestionService().load(tmp_path)
        
        # Для оценки времени НЕ запускаем LLM, а делаем быструю прикидку
        from app.services.nlp.service import extract_entities, extract_numbers, extract_triples
        fast_entities = extract_entities(doc.text)
        fast_numbers = extract_numbers(doc.text)
        fast_triples = extract_triples(doc.text)
        
        # Добавляем примерное кол-во умных триплетов (10 штук = 20 узлов + 10 связей)
        llm_triples_estimate = 10 
        
        entities_count = len(fast_entities) + len(fast_numbers) + (len(fast_triples) * 2) + (llm_triples_estimate * 2) + 1
        
        # Оценка времени: 0.008s на быструю сущность + ~10-15 секунд на LLM API вызовы
        estimated_time = max(1, int(entities_count * 0.008)) + 12
        
        return {
            "filename": file.filename,
            "estimated_nodes": entities_count,
            "estimated_time_seconds": estimated_time
        }
    finally:
        os.unlink(tmp_path)


@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    service: Annotated[GraphService, Depends(get_graph_service)] = None,
    _user: Annotated[User, Depends(get_current_user)] = None,
):
    from app.services.ingestion.service import IngestionService
    from app.services.nlp.service import extract_from_text
    from app.schemas.graph import EntityCreate, EntityType, RelationCreate, RelationType
    from fastapi.responses import StreamingResponse
    import json
    import uuid
    
    # Save uploaded file to temp dir
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
        
    def generate_progress():
        try:
            doc = IngestionService().load(tmp_path)
            
            # 1. Быстрое извлечение
            extraction = extract_from_text(doc.text)
            created = []
            
            # Оценочное количество чанков текста для LLM (1 чанк = 1 операция прогресс-бара)
            chunk_count = (len(doc.text) // 4000) + 1
            
            total_items = 1 + len(extraction.entities) + len(extraction.numbers) + len(extraction.triples) + chunk_count
            processed_items = 0
            
            # Create PUBLICATION node
            doc_node_id = service.upsert_entity(
                EntityCreate(
                    type=EntityType.PUBLICATION,
                    name=file.filename,
                    properties={"raw_text": doc.text},
                    source=doc.doc_id,
                )
            )
            created.append(doc_node_id)
            processed_items += 1
            yield json.dumps({"processed": processed_items, "total": total_items}) + "\n"
            
            # Process regular entities
            for ent in extraction.entities:
                label = ent.label
                ent_type = EntityType(label) if label in [e.value for e in EntityType] else EntityType.PROPERTY
                eid = service.upsert_entity(
                    EntityCreate(type=ent_type, name=ent.text, properties={}, source=doc.doc_id)
                )
                created.append(eid)
                service.create_relation(
                    RelationCreate(source_id=eid, target_id=doc_node_id, type=RelationType.DESCRIBED_IN, properties={}, source=doc.doc_id)
                )
                processed_items += 1
                if processed_items % 50 == 0:
                    yield json.dumps({"processed": processed_items, "total": total_items}) + "\n"
                
            # Process numbers
            for num in extraction.numbers:
                eid = service.upsert_entity(
                    EntityCreate(
                        type=EntityType.PROPERTY,
                        name=num.text,
                        properties={"value": num.value, "unit": num.unit, "op": num.op} if hasattr(num, "value") else {},
                        source=doc.doc_id,
                    )
                )
                created.append(eid)
                service.create_relation(
                    RelationCreate(source_id=eid, target_id=doc_node_id, type=RelationType.DESCRIBED_IN, properties={}, source=doc.doc_id)
                )
                processed_items += 1
                if processed_items % 50 == 0:
                    yield json.dumps({"processed": processed_items, "total": total_items}) + "\n"
                
            # Create relations (fast triples)
            for triple in extraction.triples:
                source_id = service.upsert_entity(
                    EntityCreate(type=EntityType.PROCESS, name=triple.subject, properties={}, source=doc.doc_id)
                )
                target_id = service.upsert_entity(
                    EntityCreate(type=EntityType.PROCESS, name=triple.object, properties={}, source=doc.doc_id)
                )
                service.create_relation(
                    RelationCreate(
                        source_id=source_id,
                        target_id=target_id,
                        type=RelationType(triple.predicate) if triple.predicate in [e.value for e in RelationType] else RelationType.USES_MATERIAL,
                        properties={},
                        source=doc.doc_id,
                    )
                )
                processed_items += 1
                if processed_items % 50 == 0:
                    yield json.dumps({"processed": processed_items, "total": total_items}) + "\n"
                    
            # 2. Умное извлечение через LLM в фоне с потоковой отдачей прогресса
            from app.services.nlp.service import extract_triples_llm_iter
            for llm_triples_batch in extract_triples_llm_iter(doc.text):
                # Добавляем новые триплеты в общий список
                extraction.triples.extend(llm_triples_batch)
                
                # Добавляем каждый триплет в базу
                for triple in llm_triples_batch:
                    source_id = service.upsert_entity(
                        EntityCreate(type=EntityType.PROCESS, name=triple.subject, properties={}, source=doc.doc_id)
                    )
                    target_id = service.upsert_entity(
                        EntityCreate(type=EntityType.PROCESS, name=triple.object, properties={}, source=doc.doc_id)
                    )
                    service.create_relation(
                        RelationCreate(
                            source_id=source_id,
                            target_id=target_id,
                            type=RelationType(triple.predicate) if triple.predicate in [e.value for e in RelationType] else RelationType.USES_MATERIAL,
                            properties={},
                            source=doc.doc_id,
                        )
                    )
                    created.append(source_id)
                    created.append(target_id)
                    
                processed_items += 1  # 1 чанк обработан
                yield json.dumps({"processed": processed_items, "total": total_items}) + "\n"
                
            # Final result
            yield json.dumps({
                "status": "success",
                "filename": file.filename,
                "entities_extracted": len(created),
                "triples_extracted": len(extraction.triples),
                "processed": total_items,
                "total": total_items
            }) + "\n"
        finally:
            os.unlink(tmp_path)

    return StreamingResponse(generate_progress(), media_type="application/x-ndjson")

