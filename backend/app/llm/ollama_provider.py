import json

import requests

from app.core.config import settings
from app.llm.base import LLMProvider


class OllamaProvider(LLMProvider):

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        response = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": settings.LLM_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
            },
            timeout=120,
        )

        print("Status:", response.status_code)
        print("Body:", response.text)

        response.raise_for_status()

        return response.json()["response"]

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ):
        print("Calling Ollama...")

        response = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": settings.LLM_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": True,
            },
            stream=True,
            timeout=120,
        )
        print(response.status_code)     

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            chunk = json.loads(line.decode("utf-8"))

            if "response" in chunk:
                print(chunk["response"])
                yield chunk["response"]

            if chunk.get("done"):
                print("finished")
                break