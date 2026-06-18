from app.core.config import settings
from app.schemas.task import TaskProgress, TaskResponse
from app.services.draft_video_export import generate_draft_video_export
from app.workers.tasks import (
    create_task,
    set_task_failed,
    set_task_progress,
    set_task_result,
    set_task_running,
)


def run_draft_video_export_task(payload: dict, task_id: str | None = None) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            total_rows=1,
            current_message="视频 JSON 转换任务已创建。",
        )
    )
    if task_id is not None:
        task = task.model_copy(update={"task_id": task_id})
        from app.workers import tasks

        tasks._TASKS[task_id] = task

    progress = TaskProgress(
        phase="preparing_context",
        model=settings.openai_model,
        current_row=1,
        total_rows=1,
        percent=15,
        current_message="正在读取草稿内容。",
    )
    _publish(set_task_running(task.task_id, progress))

    try:
        draft_id = str(payload.get("draft_id") or "")
        progress = progress.model_copy(
            update={
                "phase": "calling_llm",
                "percent": 55,
                "current_message": "正在调用 LLM 生成视频处理 JSON。",
            }
        )
        _publish(set_task_progress(task.task_id, progress))
        result = generate_draft_video_export(draft_id)
        progress = progress.model_copy(
            update={
                "phase": "saving_result",
                "percent": 85,
                "model": result.model or settings.openai_model,
                "current_message": "正在保存视频 JSON 历史记录。",
            }
        )
        _publish(set_task_progress(task.task_id, progress))
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
            "model": result.model or settings.openai_model,
            "current_message": "视频 JSON 转换已完成。",
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
