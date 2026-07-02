__all__ = ["Base", "SessionLocal", "engine", "get_db", "get_neo4j", "Neo4jDriver"]


def __getattr__(name: str):
    if name in {"Neo4jDriver", "get_neo4j"}:
        from app.db.neo4j.driver import Neo4jDriver, get_neo4j

        return {"Neo4jDriver": Neo4jDriver, "get_neo4j": get_neo4j}[name]
    raise AttributeError(name)
