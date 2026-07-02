"""CLI: загрузка тестового документа, извлечение сущностей, запись в граф."""

from __future__ import annotations

import argparse
import sys

from app.db.neo4j.driver import get_neo4j
from app.logging_config import setup_logging
from app.services.graph.service import GraphService
from app.services.ingestion.service import IngestionService
from app.services.nlp.service import NLPService
from app.schemas.graph import EntityCreate, EntityType


def main() -> int:
    parser = argparse.ArgumentParser(description="Импорт документа в граф знаний")
    parser.add_argument("path", help="Путь к файлу")
    args = parser.parse_args()

    setup_logging()

    doc = IngestionService().load(args.path)
    extraction = NLPService().extract(doc.text, language=doc.language)
    graph = GraphService(get_neo4j())
    graph.init_schema()

    created: list[str] = []
    for ent in extraction.entities:
        eid = graph.upsert_entity(
            EntityCreate(
                type=EntityType(ent.type) if ent.type in EntityType._value2member_map_ else EntityType.PROPERTY,
                name=ent.name,
                properties={"value": ent.value, "unit": ent.unit, "op": ent.op} if ent.value is not None else {},
                source=doc.doc_id,
            )
        )
        created.append(eid)

    print(f"OK doc_id={doc.doc_id} entities={len(created)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
