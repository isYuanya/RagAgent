from fastapi import APIRouter

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.workflows.copy_generation import run_generation_workflow

router = APIRouter()


@router.post("", response_model=GenerateResponse)
def generate(payload: GenerateRequest) -> GenerateResponse:
    return run_generation_workflow(payload)
