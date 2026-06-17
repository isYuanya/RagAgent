from fastapi import APIRouter, HTTPException

from app.schemas.composition import (
    AcceptCompositionRequest,
    AcceptCompositionResponse,
    AutoCompositionRequest,
)
from app.schemas.task import TaskResponse
from app.services import compositions, drafts
from app.workers.recommendation_queue import enqueue_auto_composition

router = APIRouter()


@router.post("/auto-draft", response_model=TaskResponse)
def auto_draft(payload: AutoCompositionRequest):
    return enqueue_auto_composition(payload)


@router.post("/accepted", response_model=AcceptCompositionResponse)
def accept_composition(payload: AcceptCompositionRequest):
    try:
        return compositions.accept_composition(payload)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except compositions.CompositionTaskNotFoundError:
        raise HTTPException(status_code=404, detail="Composition task not found") from None
    except compositions.CompositionCandidateNotFoundError:
        raise HTTPException(status_code=404, detail="Composition candidate not found") from None
