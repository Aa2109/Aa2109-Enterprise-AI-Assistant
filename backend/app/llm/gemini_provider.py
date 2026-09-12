from typing import Iterator

from google import genai
from google.genai import types

from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import LLMProvider

from opentelemetry import trace
tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)

import time
from app.observability import metrics

class GeminiProvider(LLMProvider):

    def __init__(self) -> None:
        # The request timeout belongs on the client's http_options
        # (in milliseconds), NOT on GenerateContentConfig, which rejects a
        # `timeout` field. Setting it here applies uniformly to generate(),
        # stream() and generate_structured().
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=int(settings.LLM_TIMEOUT_SECONDS * 1000),
            ),
        )

        self.model = settings.LLM_MODEL

    def _record_token_metrics(
        self,
        response,
        operation: str,
    ) -> None:

        usage = getattr(
            response,
            "usage_metadata",
            None,
        )

        if not usage:
            return

        input_tokens = (
            getattr(
                usage,
                "prompt_token_count",
                0,
            )
            or 0
        )

        output_tokens = (
            getattr(
                usage,
                "candidates_token_count",
                0,
            )
            or 0
        )

        total_tokens = (
            getattr(
                usage,
                "total_token_count",
                0,
            )
            or 0
        )

        labels = {
            "provider": "gemini",
            "operation": operation,
        }

        metrics.llm_input_tokens.add(
            input_tokens,
            labels,
        )

        metrics.llm_output_tokens.add(
            output_tokens,
            labels,
        )

        metrics.llm_total_tokens.add(
            total_tokens,
            labels,
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        with tracer.start_as_current_span(
            "llm.generate"
        ) as span:

            span.set_attribute(
                "llm.provider",
                "gemini",
            )

            span.set_attribute(
                "llm.model",
                self.model,
            )

            span.set_attribute(
                "llm.operation",
                "generate",
            )

            span.set_attribute(
                "llm.input_length",
                len(user_prompt),
            )

            start_time = time.perf_counter()
            metrics.llm_calls.add(
                1,
                {
                    "provider": "gemini",
                    "operation": "generate",
                },
            )

            try:

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                )
                self._record_token_metrics(
                    response,
                    operation="generate",
                )

                answer = response.text or ""

                span.set_attribute(
                    "llm.output_length",
                    len(answer),
                )

                span.set_attribute(
                    "llm.success",
                    True,
                )

                return answer

            except Exception as exc:

                span.set_attribute(
                    "llm.success",
                    False,
                )

                span.record_exception(
                    exc
                )

                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        str(exc),
                    )
                )

                raise

            finally:

                metrics.llm_duration_seconds.record(
                    time.perf_counter() - start_time,
                    {
                        "provider": "gemini",
                        "operation": "generate",
                    },
                )

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:

        response_stream = self.client.models.generate_content_stream(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )

        for chunk in response_stream:

            if chunk.text:
                yield chunk.text

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:

        response_schema = schema.model_json_schema()

        def remove_unsupported_fields(value):

            if isinstance(value, dict):

                value.pop(
                    "additionalProperties",
                    None,
                )

                for child in value.values():
                    remove_unsupported_fields(child)

            elif isinstance(value, list):

                for child in value:
                    remove_unsupported_fields(child)

        remove_unsupported_fields(
            response_schema
        )

        with tracer.start_as_current_span(
            "llm.generate_structured"
        ) as span:

            span.set_attribute(
                "llm.provider",
                "gemini",
            )

            span.set_attribute(
                "llm.model",
                self.model,
            )

            span.set_attribute(
                "llm.operation",
                "structured",
            )

            span.set_attribute(
                "llm.input_length",
                len(user_prompt),
            )

            start_time = time.perf_counter()
            metrics.llm_calls.add(
                1,
                {
                    "provider": "gemini",
                    "operation": "structured",
                },
            )

            try:

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                )

                self._record_token_metrics(
                    response,
                    operation="structured",
                )

                if not response.text:

                    raise ValueError(
                        "Gemini returned empty structured response"
                    )

                result = schema.model_validate_json(
                    response.text
                )

                return result

            except Exception as exc:

                span.record_exception(
                    exc
                )

                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        str(exc),
                    )
                )
                raise
            finally:
                metrics.llm_duration_seconds.record(
                    time.perf_counter() - start_time,
                    {
                        "provider": "gemini",
                        "operation": "structured",
                    },
                )