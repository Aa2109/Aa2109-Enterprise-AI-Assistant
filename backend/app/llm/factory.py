from app.core.config import settings

from app.llm.openai_provider import OpenAILLMProvider
from app.llm.ollama_provider import OllamaProvider


class LLMFactory:

    @staticmethod
    def get_provider():

        if settings.LLM_PROVIDER == "ollama":
            return OllamaProvider()

        return OpenAILLMProvider()