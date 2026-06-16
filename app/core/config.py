from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    # 应用显示名称，主要用于健康检查、日志和文档展示。
    app_name: str = "RagAgent"
    # 运行环境标识，例如 local、test、production。
    app_env: str = "local"
    # 后端 API 的统一路由前缀。
    api_prefix: str = "/api"
    # 允许跨源访问的前端源列表，多个地址用逗号分隔。
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])
    # 允许跨源访问的前端源正则，便于本地端口变化时仍能访问。
    cors_origin_regex: str | None = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # PostgreSQL 连接地址，用于持久化文案、知识库和拆解结果。
    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"
    # Redis 连接地址，用于导入队列、任务状态和兜底缓存。
    redis_url: str = "redis://localhost:6379/0"
    # Milvus 连接地址，后续用于向量检索和 RAG 召回。
    milvus_uri: str = "http://localhost:19530"
    # 本地文件存储目录，用于测试文件、日志或后续上传附件。
    storage_dir: Path = Path("storage")

    # OpenAI API Key；为空时 LLM 拆解接口会返回配置错误。
    openai_api_key: str | None = None
    # OpenAI 兼容接口地址，可替换为兼容供应商的 base url。
    openai_base_url: str = "https://api.openai.com/v1"
    # 文案拆解、审核等文本任务使用的默认模型。
    openai_model: str = "gpt-4.1-mini"
    # 向量化模型名称，供后续知识库检索使用。
    embedding_model: str = "text-embedding-3-small"
    # LLM 自动审核通过阈值；低于该置信度的文案进入人工再审。
    copy_auto_approve_min_confidence: float = 0.85
    # Minimum confidence for generated fragments to become immediately usable.
    fragment_auto_approve_min_confidence: float = 0.85

    # 是否启用 LangSmith tracing。
    langsmith_tracing: bool = False
    # LangSmith API Key；未开启 tracing 时可以为空。
    langsmith_api_key: str | None = None
    # LangSmith 项目名称，用于区分本地和不同环境的调用轨迹。
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


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


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
        copy_auto_approve_min_confidence=_env_float("COPY_AUTO_APPROVE_MIN_CONFIDENCE", 0.85),
        fragment_auto_approve_min_confidence=_env_float(
            "FRAGMENT_AUTO_APPROVE_MIN_CONFIDENCE", 0.85
        ),
        langsmith_tracing=_env_bool("LANGSMITH_TRACING", False),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY") or None,
        langsmith_project=os.getenv("LANGSMITH_PROJECT", "rag-agent-local"),
    )


settings = get_settings()
