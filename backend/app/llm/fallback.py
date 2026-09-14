import logging

from collections.abc import Iterator
from pydantic import BaseModel

from opentelemetry import trace

from app.llm.base import LLMProvider

from app.observability import metrics


logger = logging.getLogger(
    __name__,
)

tracer = trace.get_tracer(
    "enterprise-ai-assistant",
)


class FallbackLLMProvider(LLMProvider):

    def __init__(
        self,
        providers: list[LLMProvider],
    ) -> None:
        self.providers = providers

        logger.info(
            "LLM fallback chain configured "
            "providers=%s",
            [
                type(p).__name__
                for p in providers
            ],
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        last_error = None

        for index, provider in enumerate(
            self.providers,
        ):
            provider_name = (
                type(provider).__name__
            )

            try:

                with tracer.start_as_current_span(
                    "llm.fallback.generate"
                ) as span:

                    span.set_attribute(
                        "llm.provider",
                        provider_name,
                    )

                    span.set_attribute(
                        "llm.fallback.attempt",
                        index + 1,
                    )

                    result = provider.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    )

                    if index > 0:

                        logger.warning(
                            "LLM fallback succeeded "
                            "provider=%s "
                            "after %s failures",
                            provider_name,
                            index,
                        )

                    return result

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "LLM fallback provider=%s "
                    "failed error=%s",
                    provider_name,
                    exc,
                )

                self._record_fallback_metric(
                    from_provider=provider_name,
                )

                continue

        raise last_error

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:

        last_error = None

        for index, provider in enumerate(
            self.providers,
        ):
            provider_name = (
                type(provider).__name__
            )

            try:

                with tracer.start_as_current_span(
                    "llm.fallback.stream"
                ) as span:

                    span.set_attribute(
                        "llm.provider",
                        provider_name,
                    )

                    span.set_attribute(
                        "llm.fallback.attempt",
                        index + 1,
                    )

                    yield from provider.stream(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    )

                    if index > 0:

                        logger.warning(
                            "LLM fallback stream "
                            "succeeded provider=%s "
                            "after %s failures",
                            provider_name,
                            index,
                        )

                    return

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "LLM fallback stream "
                    "provider=%s failed error=%s",
                    provider_name,
                    exc,
                )

                self._record_fallback_metric(
                    from_provider=provider_name,
                )

                continue

        raise last_error

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:

        last_error = None

        for index, provider in enumerate(
            self.providers,
        ):
            provider_name = (
                type(provider).__name__
            )

            try:

                with tracer.start_as_current_span(
                    "llm.fallback.generate_structured"
                ) as span:

                    span.set_attribute(
                        "llm.provider",
                        provider_name,
                    )

                    span.set_attribute(
                        "llm.fallback.attempt",
                        index + 1,
                    )

                    result = (
                        provider.generate_structured(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            schema=schema,
                        )
                    )

                    if index > 0:

                        logger.warning(
                            "LLM fallback structured "
                            "succeeded provider=%s "
                            "after %s failures",
                            provider_name,
                            index,
                        )

                    return result

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "LLM fallback structured "
                    "provider=%s failed error=%s",
                    provider_name,
                    exc,
                )

                self._record_fallback_metric(
                    from_provider=provider_name,
                )

                continue

        raise last_error

    @staticmethod
    def _record_fallback_metric(
        from_provider: str,
    ) -> None:

        try:

            metrics.llm_fallback.add(
                1,
                {
                    "from_provider": from_provider,
                },
            )

        except Exception:

            pass
