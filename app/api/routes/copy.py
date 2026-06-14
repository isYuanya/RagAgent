from fastapi import APIRouter

from app.schemas.copy import CopyAnalysisRequest, CopyAnalysisResponse
from app.workflows.copy_analysis import run_analysis_workflow

router = APIRouter()


@router.post("/analyze", response_model=CopyAnalysisResponse)
def analyze(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    return run_analysis_workflow(payload)
