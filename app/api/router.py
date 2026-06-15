from fastapi import APIRouter

from app.api.routes import copy, feedback, generate, health, knowledge, tasks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(copy.router, prefix="/copy", tags=["copy"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
