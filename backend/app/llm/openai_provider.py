from collections.abc import Iterator

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import LLMProvider

class OpenAILLMProvider(LLMProvider):

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        self.model = settings.LLM_MODEL

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        response = self.client.responses.create(
            model=self.model,
            input=[
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

        return response.output_text or ""

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:

        stream = self.client.responses.create(
            model=self.model,
            input=[
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

        for event in stream:

            if event.type == "response.output_text.delta":
                if event.delta:
                    yield event.delta

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            text_format=schema,
        )

        if response.output_parsed is None:
            raise ValueError(
                "OpenAI returned empty structured response"
            )

        return response.output_parsed