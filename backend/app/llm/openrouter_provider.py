from collections.abc import Iterator

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import LLMProvider

class OpenRouterProvider(LLMProvider):

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        self.model = settings.LLM_MODEL

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=settings.LLM_MAX_TOKENS,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        return response.choices[0].message.content or ""

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:

        stream = self.client.chat.completions.create(
            model=self.model,
            max_tokens=settings.LLM_MAX_TOKENS,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            stream=True,
        )

        for chunk in stream:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if delta.content:
                yield delta.content

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=settings.LLM_MAX_TOKENS,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    # strict grammar validation requires additionalProperties:
                    # false on every object and all properties in `required`,
                    # which pydantic's model_json_schema() does not emit (and an
                    # open dict field like tool_arguments cannot satisfy at all),
                    # so strict mode 400s on strict-enforcing models. Keep it
                    # off; the client-side model_validate_json below still
                    # enforces the schema.
                    "strict": False,
                    "schema": schema.model_json_schema(),
                },
            },
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                "OpenRouter returned empty structured response"
            )

        return schema.model_validate_json(content)
