"""CLI: загрузка тестового документа, извлечение сущностей, запись в граф."""

from __future__ import annotations

import argparse
import sys

from app.db.neo4j.driver import get_neo4j
from app.logging_config import setup_logging
from app.services.graph.service import GraphService
from app.services.ingestion.service import IngestionService
from app.services.nlp.service import extract_from_text
from app.schemas.graph import EntityCreate, EntityType


def main() -> int:
    parser = argparse.ArgumentParser(description="Импорт документа в граф знаний")
    parser.add_argument("path", help="Путь к файлу или папке")
    args = parser.parse_args()

    setup_logging()

    from pathlib import Path
    target_path = Path(args.path)
    
    files_to_process = []
    if target_path.is_file():
        files_to_process.append(target_path)
    elif target_path.is_dir():
        for p in target_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in IngestionService.SUPPORTED_SUFFIXES:
                files_to_process.append(p)
    else:
        print(f"Путь {args.path} не найден.")
        return 1

    if not files_to_process:
        print("Подходящие файлы не найдены.")
        return 0

    graph = GraphService(get_neo4j())
    graph.init_schema()

    total_entities = 0
    
    for file_path in files_to_process:
        print(f"Обработка файла: {file_path}")
        try:
            doc = IngestionService().load(file_path)
            extraction = extract_from_text(doc.text)
            
            created: list[str] = []
            
            # Create PUBLICATION node for document text
            doc_node_id = graph.upsert_entity(
                EntityCreate(
                    type=EntityType.PUBLICATION,
                    name=str(file_path.name),
                    properties={"raw_text": doc.text},
                    source=doc.doc_id,
                )
            )
            created.append(doc_node_id)
            
            from app.schemas.graph import RelationCreate, RelationType
            
            # Process regular entities
            for ent in extraction.entities:
                label = ent.label
                ent_type = EntityType(label) if label in [e.value for e in EntityType] else EntityType.PROPERTY
                eid = graph.upsert_entity(
                    EntityCreate(
                        type=ent_type,
                        name=ent.text,
                        properties={},
                        source=doc.doc_id,
                    )
                )
                created.append(eid)
                graph.create_relation(
                    RelationCreate(
                        source_id=eid,
                        target_id=doc_node_id,
                        type=RelationType.DESCRIBED_IN,
                        properties={},
                        source=doc.doc_id,
                    )
                )
                
            # Create numbers
            for num in extraction.numbers:
                eid = graph.upsert_entity(
                    EntityCreate(
                        type=EntityType.PROPERTY,
                        name=num.text,
                        properties={"value": num.value, "unit": num.unit, "op": num.op} if hasattr(num, "value") else {},
                        source=doc.doc_id,
                    )
                )
                created.append(eid)
                graph.create_relation(
                    RelationCreate(
                        source_id=eid,
                        target_id=doc_node_id,
                        type=RelationType.DESCRIBED_IN,
                        properties={},
                        source=doc.doc_id,
                    )
                )
                
            # Create relations
            for triple in extraction.triples:
                source_id = graph.upsert_entity(
                    EntityCreate(type=EntityType.PROCESS, name=triple.subject, properties={}, source=doc.doc_id)
                )
                target_id = graph.upsert_entity(
                    EntityCreate(type=EntityType.PROCESS, name=triple.object, properties={}, source=doc.doc_id)
                )
                from app.schemas.graph import RelationCreate, RelationType
                graph.create_relation(
                    RelationCreate(
                        source_id=source_id,
                        target_id=target_id,
                        type=RelationType(triple.predicate) if triple.predicate in [e.value for e in RelationType] else RelationType.USES_MATERIAL,
                        properties={},
                        source=doc.doc_id,
                    )
                )

            print(f"OK doc_id={doc.doc_id} entities={len(created)} triples={len(extraction.triples)}")
            total_entities += len(created)
        except Exception as e:
            print(f"Ошибка при обработке {file_path}: {e}")

    print(f"Завершено. Всего извлечено сущностей: {total_entities}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
