from redis.exceptions import RedisError

from app.core.config import settings
from app.schemas.composition import AutoCompositionRequest
from app.schemas.diagnostic import CopyDiagnosisRequest
from app.schemas.recommendation import NextSentenceRecommendationRequest
from app.schemas.task import TaskProgress, TaskResponse
from app.services.composition_jobs import run_auto_composition_task
from app.services.diagnostic_jobs import run_copy_diagnosis_task
from app.services.draft_video_export_jobs import run_draft_video_export_task
from app.services.recommendation_jobs import run_next_sentence_task
from app.workers.queue import get_queue
from app.workers.tasks import create_task, set_task_running


def enqueue_next_sentence_recommendation(
    payload: NextSentenceRecommendationRequest,
) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            total_rows=1,
            current_message="Recommendation task created.",
        )
    )
    try:
        queue = get_queue("recommendation")
        job = queue.enqueue(
            run_next_sentence_task,
            payload.model_dump(),
            task.task_id,
            job_id=task.task_id,
            result_ttl=3600,
            failure_ttl=86400,
        )
        progress = task.progress.model_copy(
            update={"current_message": f"Recommendation task queued: {job.id}."}
        )
        return set_task_running(task.task_id, progress)
    except RedisError:
        return run_next_sentence_task(payload.model_dump(), task.task_id)


def enqueue_auto_composition(payload: AutoCompositionRequest) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            total_rows=1,
            current_message="Auto-composition task created.",
        )
    )
    try:
        queue = get_queue("recommendation")
        job = queue.enqueue(
            run_auto_composition_task,
            payload.model_dump(),
            task.task_id,
            job_id=task.task_id,
            result_ttl=3600,
            failure_ttl=86400,
        )
        progress = task.progress.model_copy(
            update={"current_message": f"Auto-composition task queued: {job.id}."}
        )
        return set_task_running(task.task_id, progress)
    except RedisError:
        return run_auto_composition_task(payload.model_dump(), task.task_id)


def enqueue_copy_diagnosis(payload: CopyDiagnosisRequest) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            total_rows=1,
            current_message="Copy diagnosis task created.",
        )
    )
    try:
        queue = get_queue("recommendation")
        job = queue.enqueue(
            run_copy_diagnosis_task,
            payload.model_dump(),
            task.task_id,
            job_id=task.task_id,
            result_ttl=3600,
            failure_ttl=86400,
        )
        progress = task.progress.model_copy(
            update={"current_message": f"Copy diagnosis task queued: {job.id}."}
        )
        return set_task_running(task.task_id, progress)
    except RedisError:
        return run_copy_diagnosis_task(payload.model_dump(), task.task_id)


def enqueue_draft_video_export(draft_id: str) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            total_rows=1,
            current_message="视频 JSON 转换任务已创建。",
        )
    )
    payload = {"draft_id": draft_id}
    try:
        queue = get_queue("recommendation")
        job = queue.enqueue(
            run_draft_video_export_task,
            payload,
            task.task_id,
            job_id=task.task_id,
            result_ttl=3600,
            failure_ttl=86400,
        )
        progress = task.progress.model_copy(
            update={"current_message": f"视频 JSON 转换任务已入队：{job.id}。"}
        )
        return set_task_running(task.task_id, progress)
    except RedisError:
        return run_draft_video_export_task(payload, task.task_id)
