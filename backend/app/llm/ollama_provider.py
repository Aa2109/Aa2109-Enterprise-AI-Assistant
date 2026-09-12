import json

from pydantic import BaseModel
import requests

from app.core.config import settings
from app.llm.base import LLMProvider


class OllamaProvider(LLMProvider):

    def __init__(self) -> None:
        # Store the model on the instance (like the other providers) so
        # LLMFactory's fallback-model override (`if hasattr(provider,
        # "model"): provider.model = model`) actually applies. Otherwise a
        # cross-provider fallback would send the primary's model name.
        self.model = settings.LLM_MODEL

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        response = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": self.model,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        return response.json()["response"]

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ):

        response = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": self.model,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": True,
            },
            stream=True,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )   

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            chunk = json.loads(line.decode("utf-8"))

            if "response" in chunk:
                yield chunk["response"]

            if chunk.get("done"):
                break

    def generate_structured(
    self,
    system_prompt: str,
    user_prompt: str,
    schema: type[BaseModel],    
    ) -> BaseModel:

        response = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": self.model,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "format": schema.model_json_schema(),
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        data = response.json()["response"]

        return schema.model_validate_json(data)