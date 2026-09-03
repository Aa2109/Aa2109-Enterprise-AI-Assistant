
from app.llm.factory import LLMFactory
from app.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    return LLMFactory.get_provider()

def get_llm() -> LLMProvider:
    return get_llm_provider()
    
'''
from fastapi import Depends

from app.llm.base import LLMProvider
from app.llm.factory import LLMFactory
from app.schemas.chat import ChatRequest


def get_llm() -> LLMProvider:
    return LLMFactory.get_provider()

@router.post("/chat")
def chat(
    request: ChatRequest,
    llm: LLMProvider = Depends(get_llm),
):
    answer = llm.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt=request.message,
    )

    return {
        "answer": answer
    }
'''