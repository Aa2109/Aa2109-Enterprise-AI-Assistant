from app.core.config import settings

from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.openai_provider import OpenAILLMProvider
from app.llm.openrouter_provider import OpenRouterProvider
from app.llm.ollama_provider import OllamaProvider


class LLMFactory:

    @staticmethod
    def get_provider() -> LLMProvider:

        provider = settings.LLM_PROVIDER.lower()

        if provider == "ollama":
            return OllamaProvider()

        if provider == "openai":
            return OpenAILLMProvider()

        if provider == "openrouter":
            return OpenRouterProvider()

        if provider == "gemini":
            return GeminiProvider()

        raise ValueError(
            f"Unsupported LLM provider: {settings.LLM_PROVIDER}"
        )
