from openai import OpenAI

from app.core.config import settings
from app.llm.base import LLMProvider


class OpenAILLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL

    def generate(self, system_prompt: str, user_prompt: str) -> str:
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

        return response.output_text

    def stream(self, prompt: str):

        stream = self.client.responses.create(
            model=self.model,
            input=prompt,
            stream=True,
        )

        for event in stream:

            if event.type == "response.output_text.delta":
                yield event.delta