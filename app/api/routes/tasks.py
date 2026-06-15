from fastapi import APIRouter, HTTPException

from app.schemas.task import TaskResponse
from app.workers.queue import get_queue
from app.workers.tasks import get_task

router = APIRouter()


@router.get("/{task_id}", response_model=TaskResponse)
def read_task(task_id: str) -> TaskResponse:
    rq_task = _read_rq_task(task_id)
    if rq_task is not None:
        return rq_task

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _read_rq_task(task_id: str) -> TaskResponse | None:
    try:
        from rq.job import Job

        job = Job.fetch(task_id, connection=get_queue("copy_import").connection)
    except Exception:
        return None

    task_data = job.meta.get("task")
    if isinstance(task_data, dict):
        return TaskResponse.model_validate(task_data)

    status = job.get_status(refresh=True)
    return TaskResponse(task_id=task_id, status=str(status))
