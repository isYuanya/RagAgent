from typing import Protocol

from app.core.config import settings


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return a text completion for a prompt."""


class OpenAICompatibleLLMClient:
    def __init__(self) -> None:
        self.model = settings.openai_model
        self.base_url = settings.openai_base_url

    def complete(self, prompt: str) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=self.base_url,
                model=self.model,
                timeout=settings.openai_timeout,
                max_retries=1,
            )
            response = llm.invoke(prompt)
        except Exception as exc:
            raise RuntimeError(
                "LLM call failed "
                f"(model={self.model!r}, base_url={self.base_url!r}): {exc}"
            ) from exc

        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(str(item) for item in content)
        return str(content)


def get_llm_client() -> LLMClient:
    return OpenAICompatibleLLMClient()
