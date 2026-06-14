from uuid import uuid4

from app.schemas.task import TaskResponse

_TASKS: dict[str, TaskResponse] = {}


def create_task(status: str = "queued", result: dict | None = None) -> TaskResponse:
    task = TaskResponse(task_id=str(uuid4()), status=status, result=result)
    _TASKS[task.task_id] = task
    return task


def get_task(task_id: str) -> TaskResponse | None:
    return _TASKS.get(task_id)


def set_task_result(task_id: str, result: dict) -> TaskResponse:
    task = TaskResponse(task_id=task_id, status="finished", result=result)
    _TASKS[task_id] = task
    return task
