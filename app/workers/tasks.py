from uuid import uuid4

from app.schemas.task import TaskProgress, TaskResponse

_TASKS: dict[str, TaskResponse] = {}


def create_task(
    status: str = "queued",
    result: dict | None = None,
    progress: TaskProgress | None = None,
) -> TaskResponse:
    task = TaskResponse(task_id=str(uuid4()), status=status, result=result, progress=progress)
    _TASKS[task.task_id] = task
    return task


def get_task(task_id: str) -> TaskResponse | None:
    return _TASKS.get(task_id)


def set_task_result(task_id: str, result: dict) -> TaskResponse:
    current = _TASKS.get(task_id)
    task = TaskResponse(
        task_id=task_id,
        status="finished",
        result=result,
        progress=current.progress if current else None,
    )
    _TASKS[task_id] = task
    return task


def set_task_running(task_id: str, progress: TaskProgress | None = None) -> TaskResponse:
    current = _TASKS.get(task_id)
    task = TaskResponse(
        task_id=task_id,
        status="running",
        result=current.result if current else None,
        progress=progress or (current.progress if current else None),
    )
    _TASKS[task_id] = task
    return task


def set_task_progress(task_id: str, progress: TaskProgress) -> TaskResponse:
    current = _TASKS.get(task_id)
    task = TaskResponse(
        task_id=task_id,
        status=current.status if current else "running",
        result=current.result if current else None,
        error=current.error if current else None,
        progress=progress,
    )
    _TASKS[task_id] = task
    return task


def set_task_failed(task_id: str, error: str, progress: TaskProgress | None = None) -> TaskResponse:
    current = _TASKS.get(task_id)
    task = TaskResponse(
        task_id=task_id,
        status="failed",
        result=current.result if current else None,
        error=error,
        progress=progress or (current.progress if current else None),
    )
    _TASKS[task_id] = task
    return task
