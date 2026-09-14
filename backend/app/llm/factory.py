import logging

from app.core.config import settings

from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.openai_provider import OpenAILLMProvider
from app.llm.openrouter_provider import OpenRouterProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.fallback import FallbackLLMProvider


logger = logging.getLogger(
    __name__,
)


_PROVIDER_MAP = {
    "gemini": (
        GeminiProvider,
        lambda s: bool(s.GEMINI_API_KEY),
    ),
    "openai": (
        OpenAILLMProvider,
        lambda s: bool(s.OPENAI_API_KEY),
    ),
    "openrouter": (
        OpenRouterProvider,
        lambda s: bool(s.OPENROUTER_API_KEY),
    ),
    "ollama": (
        OllamaProvider,
        lambda s: bool(s.OLLAMA_URL),
    ),
}


class LLMFactory:

    @staticmethod
    def get_provider() -> LLMProvider:

        primary_name = (
            settings.LLM_PROVIDER.lower()
        )

        primary = LLMFactory._build_provider(
            primary_name,
        )

        fallback_names = [
            name.strip().lower()
            for name in (
                settings.LLM_FALLBACK_PROVIDERS
                .split(",")
            )
            if name.strip()
        ]

        if not fallback_names:
            return primary

        fallback_providers = []

        fallback_model = (
            settings.LLM_FALLBACK_MODEL
            or settings.LLM_MODEL
        )

        for name in fallback_names:

            if name == primary_name:
                continue

            provider = (
                LLMFactory._build_provider_optional(
                    name,
                    model=fallback_model,
                )
            )

            if provider is not None:
                fallback_providers.append(
                    provider,
                )

        if not fallback_providers:
            return primary

        chain = [primary] + fallback_providers

        logger.info(
            "LLM fallback chain primary=%s "
            "fallbacks=%s",
            primary_name,
            [
                type(p).__name__
                for p in fallback_providers
            ],
        )

        return FallbackLLMProvider(
            providers=chain,
        )

    @staticmethod
    def _build_provider(
        name: str,
    ) -> LLMProvider:

        if name not in _PROVIDER_MAP:
            raise ValueError(
                f"Unsupported LLM provider: {name}"
            )

        cls, check = _PROVIDER_MAP[name]

        if not check(settings):
            raise ValueError(
                f"LLM provider '{name}' is not "
                f"configured (missing credentials)"
            )

        return cls()

    @staticmethod
    def _build_provider_optional(
        name: str,
        model: str = "",
    ) -> LLMProvider | None:

        if name not in _PROVIDER_MAP:
            logger.warning(
                "Skipping unknown fallback "
                "provider=%s",
                name,
            )
            return None

        cls, check = _PROVIDER_MAP[name]

        if not check(settings):
            logger.warning(
                "Skipping fallback provider=%s "
                "(missing credentials)",
                name,
            )
            return None

        provider = cls()

        if model and hasattr(provider, "model"):
            provider.model = model

        return provider
