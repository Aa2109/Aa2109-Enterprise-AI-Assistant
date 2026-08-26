from app.llm.factory import LLMFactory
from app.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    return LLMFactory.get_provider()

def get_llm() -> LLMProvider:
    return get_llm_provider()