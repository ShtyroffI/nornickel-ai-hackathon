from fastapi import APIRouter

from app.api.v1.endpoints import auth, graph, query, review, analytics, users, audit


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
