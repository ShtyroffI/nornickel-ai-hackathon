"""Построение и хранение графа знаний в Neo4j.

Онтология включает типы: Material, Process, Equipment, Property, Experiment,
Publication, Expert, Facility и отношения: uses_material, operates_at_condition,
produces_output, described_in, validated_by, contradicts.
"""

from __future__ import annotations

from app.db.neo4j.driver import Neo4jDriver
from app.schemas.graph import EntityCreate, EntityType, RelationCreate


CONSTRAINTS_CYPHER = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Material) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Process) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Equipment) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Property) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Experiment) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Publication) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Expert) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Facility) REQUIRE n.id IS UNIQUE",
]


class GraphService:
    def __init__(self, driver: Neo4jDriver) -> None:
        self.driver = driver

    def init_schema(self) -> None:
        for stmt in CONSTRAINTS_CYPHER:
            self.driver.run(stmt)

    def upsert_entity(self, entity: EntityCreate) -> str:
        label = entity.type.value if isinstance(entity.type, EntityType) else entity.type
        cypher = (
            f"MERGE (n:`{label}` {{name: $name}}) "
            "ON CREATE SET n.id = $id, n.created_at = timestamp() "
            "SET n += $props, n.confidence = $confidence, n.source = $source "
            "RETURN n.id AS id"
        )
        import uuid

        eid = str(uuid.uuid4())
        result = self.driver.run(
            cypher,
            {
                "name": entity.name,
                "id": eid,
                "props": entity.properties,
                "confidence": entity.confidence,
                "source": entity.source,
            },
        )
        return result[0]["id"] if result else eid

    def create_relation(self, relation: RelationCreate) -> None:
        cypher = (
            "MATCH (a {id: $source_id}), (b {id: $target_id}) "
            "MERGE (a)-[r:`" + relation.type.value + "`]->(b) "
            "SET r += $props, r.confidence = $confidence, r.source = $source"
        )
        self.driver.run(
            cypher,
            {
                "source_id": relation.source_id,
                "target_id": relation.target_id,
                "props": relation.properties,
                "confidence": relation.confidence,
                "source": relation.source,
            },
        )

    def neighborhood(self, entity_id: str, depth: int = 3) -> list[dict]:
        cypher = (
            "MATCH (n {id: $id}) "
            "OPTIONAL MATCH path = (n)-[*1.." + str(depth) + "]-(m) "
            "RETURN n, labels(n) AS n_labels, m, labels(m) AS m_labels, "
            "[rel IN relationships(path) | {start: startNode(rel).id, end: endNode(rel).id, type: type(rel), props: properties(rel)}] AS rels "
            "LIMIT 500"
        )
        return self.driver.run(cypher, {"id": entity_id})

    def search_neighborhood(self, query: str, depth: int = 2) -> list[dict]:
        # Поиск узлов по подстроке в имени (регистронезависимо) и возврат их окрестности
        # Исключаем связи described_in, чтобы не тянуть весь документ как суперузел и миллион чисел
        cypher = (
            "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($query) AND NOT n:Publication "
            "WITH n LIMIT 5 " # Берем топ-5 совпадений
            "OPTIONAL MATCH path = (n)-[*1.." + str(depth) + "]-(m) "
            "WHERE NONE(rel IN relationships(path) WHERE type(rel) = 'described_in') "
            "RETURN n, labels(n) AS n_labels, m, labels(m) AS m_labels, "
            "[rel IN relationships(path) | {start: startNode(rel).id, end: endNode(rel).id, type: type(rel), props: properties(rel)}] AS rels "
            "LIMIT 500"
        )
        return self.driver.run(cypher, {"query": query})
