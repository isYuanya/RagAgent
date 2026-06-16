from time import perf_counter
from urllib.error import URLError
from urllib.parse import SplitResult, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from redis import Redis
from redis.exceptions import RedisError
from rq import Worker
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine
from app.schemas.system import DependencyStatus, ServiceHealthStatus, SystemStatusResponse


COPY_IMPORT_QUEUE_NAME = "copy_import"
CHECK_TIMEOUT_SECONDS = 1


def get_system_status() -> SystemStatusResponse:
    services = [
        check_postgres(),
        check_redis(),
        check_copy_import_worker(),
        check_milvus(),
    ]
    return SystemStatusResponse(status=_overall_status(services), services=services)


def check_postgres() -> DependencyStatus:
    started_at = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return _service_ok(
            "postgres",
            required=True,
            endpoint=_safe_url(settings.database_url),
            started_at=started_at,
            message="PostgreSQL is reachable.",
        )
    except SQLAlchemyError as exc:
        return _service_down(
            "postgres",
            required=True,
            endpoint=_safe_url(settings.database_url),
            started_at=started_at,
            message=f"PostgreSQL is not reachable: {exc.__class__.__name__}.",
        )


def check_redis() -> DependencyStatus:
    started_at = perf_counter()
    try:
        redis = _redis()
        redis.ping()
        return _service_ok(
            "redis",
            required=True,
            endpoint=_safe_url(settings.redis_url),
            started_at=started_at,
            message="Redis is reachable.",
        )
    except RedisError as exc:
        return _service_down(
            "redis",
            required=True,
            endpoint=_safe_url(settings.redis_url),
            started_at=started_at,
            message=f"Redis is not reachable: {exc.__class__.__name__}.",
        )


def check_copy_import_worker() -> DependencyStatus:
    started_at = perf_counter()
    try:
        workers = Worker.all(connection=_redis())
    except RedisError as exc:
        return _service_down(
            "copy_import_worker",
            required=True,
            endpoint=COPY_IMPORT_QUEUE_NAME,
            started_at=started_at,
            message=f"Cannot inspect copy_import workers because Redis is unavailable: {exc.__class__.__name__}.",
        )

    active_workers = [
        worker.name
        for worker in workers
        if COPY_IMPORT_QUEUE_NAME in worker.queue_names()
    ]
    if active_workers:
        return _service_ok(
            "copy_import_worker",
            required=True,
            endpoint=COPY_IMPORT_QUEUE_NAME,
            started_at=started_at,
            message=f"{len(active_workers)} worker(s) listening on copy_import.",
        )

    return _service_down(
        "copy_import_worker",
        required=True,
        endpoint=COPY_IMPORT_QUEUE_NAME,
        started_at=started_at,
        message="No worker is listening on copy_import; import tasks may stay queued.",
    )


def check_milvus() -> DependencyStatus:
    started_at = perf_counter()
    endpoint = _safe_url(settings.milvus_uri)
    try:
        request = Request(settings.milvus_uri, method="GET")
        with urlopen(request, timeout=CHECK_TIMEOUT_SECONDS) as response:
            status_code = response.status
    except (OSError, URLError, ValueError) as exc:
        return DependencyStatus(
            name="milvus",
            required=False,
            status="degraded",
            latency_ms=_latency_ms(started_at),
            endpoint=endpoint,
            message=f"Milvus is not reachable: {exc.__class__.__name__}.",
        )

    if 200 <= status_code < 500:
        return _service_ok(
            "milvus",
            required=False,
            endpoint=endpoint,
            started_at=started_at,
            message=f"Milvus HTTP endpoint responded with {status_code}.",
        )
    return DependencyStatus(
        name="milvus",
        required=False,
        status="degraded",
        latency_ms=_latency_ms(started_at),
        endpoint=endpoint,
        message=f"Milvus HTTP endpoint responded with {status_code}.",
    )


def _overall_status(services: list[DependencyStatus]) -> ServiceHealthStatus:
    if any(service.required and service.status == "down" for service in services):
        return "down"
    if any(service.status != "ok" for service in services):
        return "degraded"
    return "ok"


def _service_ok(
    name: str,
    *,
    required: bool,
    endpoint: str | None,
    started_at: float,
    message: str,
) -> DependencyStatus:
    return DependencyStatus(
        name=name,
        required=required,
        status="ok",
        latency_ms=_latency_ms(started_at),
        endpoint=endpoint,
        message=message,
    )


def _service_down(
    name: str,
    *,
    required: bool,
    endpoint: str | None,
    started_at: float,
    message: str,
) -> DependencyStatus:
    return DependencyStatus(
        name=name,
        required=required,
        status="down",
        latency_ms=_latency_ms(started_at),
        endpoint=endpoint,
        message=message,
    )


def _latency_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _redis() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=CHECK_TIMEOUT_SECONDS,
        socket_timeout=CHECK_TIMEOUT_SECONDS,
    )


def _safe_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.netloc:
        return value

    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    if parsed.username:
        auth = f"{parsed.username}:***@"
    else:
        auth = ""
    redacted = SplitResult(
        scheme=parsed.scheme,
        netloc=f"{auth}{hostname}{port}",
        path=parsed.path,
        query="",
        fragment="",
    )
    return urlunsplit(redacted)
