from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.db.neo4j.driver import get_neo4j
from app.logging_config import setup_logging
from app.services.graph.service import GraphService


setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        GraphService(get_neo4j()).init_schema()
    except Exception:
        pass
    yield


app = FastAPI(
    title="Научный клубок API",
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
