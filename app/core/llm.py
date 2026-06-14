from typing import Protocol

from app.core.config import settings


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return a text completion for a prompt."""


class StubLLMClient:
    def complete(self, prompt: str) -> str:
        return (
            "这是 stub LLM 结果。已收到提示词，真实模型接入后会返回结构化文案拆解或生成结果。"
        )


class OpenAICompatibleLLMClient:
    def __init__(self) -> None:
        self.model = settings.openai_model
        self.base_url = settings.openai_base_url

    def complete(self, prompt: str) -> str:
        if not settings.openai_api_key:
            return StubLLMClient().complete(prompt)

        # The real provider call is intentionally deferred for the scaffold.
        # Keep this boundary stable so OpenAI, DeepSeek, Qwen-compatible gateways can plug in.
        return StubLLMClient().complete(prompt)


def get_llm_client() -> LLMClient:
    return OpenAICompatibleLLMClient()
