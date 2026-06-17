from fastapi import APIRouter

from app.api.routes import (
    copy,
    compositions,
    diagnostics,
    drafts,
    feedback,
    generate,
    health,
    knowledge,
    recommendations,
    smart_composition,
    system,
    tasks,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(copy.router, prefix="/copy", tags=["copy"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(compositions.router, prefix="/compositions", tags=["compositions"])
api_router.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])
api_router.include_router(smart_composition.router, prefix="/assistant", tags=["assistant"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
