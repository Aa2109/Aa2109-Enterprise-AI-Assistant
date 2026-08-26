from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMProvider(ABC):

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        ...

    @abstractmethod
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        ...

    @abstractmethod
    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ):
        ...