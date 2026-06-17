from redis.exceptions import RedisError

from app.core.config import settings
from app.schemas.recommendation import NextSentenceRecommendationRequest
from app.schemas.task import TaskProgress, TaskResponse
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
