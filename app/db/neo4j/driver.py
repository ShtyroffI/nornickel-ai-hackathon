from typing import Any

from neo4j import GraphDatabase

from app.config import get_settings


class Neo4jDriver:
    def __init__(self) -> None:
        settings = get_settings()
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self._driver.close()

    def run(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self._driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]


_driver: Neo4jDriver | None = None


def get_neo4j() -> Neo4jDriver:
    global _driver
    if _driver is None:
        _driver = Neo4jDriver()
    return _driver
