from fastapi import APIRouter, HTTPException

from app.schemas.task import TaskResponse
from app.workers.tasks import get_task

router = APIRouter()


@router.get("/{task_id}", response_model=TaskResponse)
def read_task(task_id: str) -> TaskResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
