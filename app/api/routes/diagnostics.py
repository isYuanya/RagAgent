from fastapi import APIRouter, HTTPException

from app.schemas.diagnostic import (
    AcceptDiagnosticRewriteRequest,
    AcceptDiagnosticRewriteResponse,
    CopyDiagnosisRequest,
)
from app.schemas.task import TaskResponse
from app.services import diagnostics, drafts
from app.workers.recommendation_queue import enqueue_copy_diagnosis

router = APIRouter()


@router.post("/copy", response_model=TaskResponse)
def diagnose_copy(payload: CopyDiagnosisRequest) -> TaskResponse:
    return enqueue_copy_diagnosis(payload)


@router.post("/accepted-rewrite", response_model=AcceptDiagnosticRewriteResponse)
def accept_diagnostic_rewrite(
    payload: AcceptDiagnosticRewriteRequest,
) -> AcceptDiagnosticRewriteResponse:
    try:
        return diagnostics.accept_diagnostic_rewrite(payload)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except diagnostics.DiagnosticTaskNotFoundError:
        raise HTTPException(status_code=404, detail="Diagnostic task not found") from None
    except diagnostics.DiagnosticCandidateNotFoundError:
        raise HTTPException(status_code=404, detail="Diagnostic candidate not found") from None
