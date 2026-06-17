from redis import Redis
from redis.exceptions import RedisError
from rq import SimpleWorker

from app.core.config import settings


def main() -> None:
    redis_conn = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        redis_conn.ping()
    except RedisError as exc:
        raise SystemExit(
            "Redis is not reachable. Start Redis first or update REDIS_URL in .env. "
            f"Current REDIS_URL: {settings.redis_url}"
        ) from exc

    worker = SimpleWorker(["copy_import", "recommendation"], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
