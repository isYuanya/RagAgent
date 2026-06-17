from app.core.config import settings
from app.schemas.composition import AutoCompositionRequest
from app.schemas.task import TaskProgress, TaskResponse
from app.services.compositions import generate_auto_composition
from app.workers.tasks import (
    create_task,
    set_task_failed,
    set_task_progress,
    set_task_result,
    set_task_running,
)


def run_auto_composition_task(payload: dict, task_id: str | None = None) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            total_rows=1,
            current_message="Auto-composition task queued.",
        )
    )
    if task_id is not None:
        task = task.model_copy(update={"task_id": task_id})
        from app.workers import tasks

        tasks._TASKS[task_id] = task

    progress = TaskProgress(
        phase="retrieving_fragments",
        model=settings.openai_model,
        current_row=1,
        total_rows=1,
        percent=20,
        current_message="Retrieving approved reference fragments.",
    )
    _publish(set_task_running(task.task_id, progress))

    try:
        request = AutoCompositionRequest.model_validate(payload)
        progress = progress.model_copy(
            update={
                "phase": "generating_compositions",
                "percent": 45,
                "current_message": "Generating auto-composition candidates.",
            }
        )
        _publish(set_task_progress(task.task_id, progress))
        result = generate_auto_composition(request)
    except Exception as exc:
        failed_progress = progress.model_copy(
            update={
                "phase": "failed",
                "percent": 100,
                "failed_count": 1,
                "current_message": str(exc),
                "errors": [{"row_number": 1, "message": str(exc)}],
            }
        )
        return _publish(set_task_failed(task.task_id, str(exc), failed_progress))

    finished_progress = progress.model_copy(
        update={
            "phase": "finished",
            "processed_count": 1,
            "success_count": 1,
            "failed_count": 0,
            "percent": 100,
            "current_message": "Auto-composition task finished.",
            "errors": [],
        }
    )
    _publish(set_task_progress(task.task_id, finished_progress))
    return _publish(set_task_result(task.task_id, result.model_dump(mode="json")))


def _publish(task: TaskResponse) -> TaskResponse:
    try:
        from rq import get_current_job

        job = get_current_job()
        if job is not None:
            job.meta["task"] = task.model_dump(mode="json")
            job.save_meta()
    except Exception:
        pass
    return task
