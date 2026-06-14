from typing import TypedDict

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.services.generation import generate_copy


class GenerationState(TypedDict, total=False):
    request: GenerateRequest
    response: GenerateResponse


def run_generation_workflow(payload: GenerateRequest) -> GenerateResponse:
    # This is the stable boundary where a LangGraph StateGraph will be attached.
    return generate_copy(payload)
