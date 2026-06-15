from redis import Redis
from rq import Queue

from app.core.config import settings


def get_queue(name: str = "default") -> Queue:
    redis_conn = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    return Queue(name, connection=redis_conn)
