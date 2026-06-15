from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    app_name: str = "RagAgent"
    app_env: str = "local"
    api_prefix: str = "/api"
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])
    cors_origin_regex: str | None = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"
    redis_url: str = "redis://localhost:6379/0"
    milvus_uri: str = "http://localhost:19530"
    storage_dir: Path = Path("storage")

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "rag-agent-local"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "RagAgent"),
        app_env=os.getenv("APP_ENV", "local"),
        api_prefix=os.getenv("API_PREFIX", "/api"),
        cors_origins=_env_list("CORS_ORIGINS", ["http://localhost:5173"]),
        cors_origin_regex=os.getenv(
            "CORS_ORIGIN_REGEX", r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        )
        or None,
        database_url=os.getenv(
            "DATABASE_URL", "postgresql+psycopg://rag:rag@localhost:5432/rag"
        ),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        milvus_uri=os.getenv("MILVUS_URI", "http://localhost:19530"),
        storage_dir=Path(os.getenv("STORAGE_DIR", "storage")),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        langsmith_tracing=_env_bool("LANGSMITH_TRACING", False),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY") or None,
        langsmith_project=os.getenv("LANGSMITH_PROJECT", "rag-agent-local"),
    )


settings = get_settings()
