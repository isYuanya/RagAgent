from redis.exceptions import RedisError

from app.core.config import settings
from app.schemas.task import TaskProgress, TaskResponse
from app.services.copy_import_jobs import run_copy_import_task, run_text_import_task
from app.workers.queue import get_queue
from app.workers.tasks import create_task, set_task_running


def enqueue_copy_import(csv_text: str, collection_ids: list[str] | None = None) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            current_message="导入任务已创建，等待 worker 处理。",
        )
    )
    try:
        queue = get_queue("copy_import")
        job = queue.enqueue(
            run_copy_import_task,
            csv_text,
            task.task_id,
            collection_ids or [],
            job_id=task.task_id,
            result_ttl=3600,
            failure_ttl=86400,
        )
        progress = task.progress.model_copy(update={"current_message": f"任务已入队：{job.id}。"})
        return set_task_running(task.task_id, progress)
    except RedisError:
        return run_copy_import_task(csv_text, task.task_id, collection_ids or [])


def enqueue_text_import(text: str, collection_ids: list[str] | None = None) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            current_message="纯文本导入任务已创建，等待 worker 处理。",
        )
    )
    try:
        queue = get_queue("copy_import")
        job = queue.enqueue(
            run_text_import_task,
            text,
            task.task_id,
            collection_ids or [],
            job_id=task.task_id,
            result_ttl=3600,
            failure_ttl=86400,
        )
        progress = task.progress.model_copy(update={"current_message": f"任务已入队：{job.id}。"})
        return set_task_running(task.task_id, progress)
    except RedisError:
        return run_text_import_task(text, task.task_id, collection_ids or [])
