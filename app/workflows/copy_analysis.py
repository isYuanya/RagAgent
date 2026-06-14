from typing import TypedDict

from app.schemas.copy import CopyAnalysisRequest, CopyAnalysisResponse
from app.services.copy_analysis import analyze_copy


class AnalysisState(TypedDict, total=False):
    request: CopyAnalysisRequest
    response: CopyAnalysisResponse


def run_analysis_workflow(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    # This is the stable boundary where a LangGraph StateGraph will be attached.
    return analyze_copy(payload)
