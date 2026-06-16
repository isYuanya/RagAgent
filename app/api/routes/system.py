from fastapi import APIRouter

from app.schemas.system import SystemStatusResponse
from app.services.system_status import get_system_status

router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse)
def status() -> SystemStatusResponse:
    return get_system_status()
