from fastapi import Depends

from app.dependencies.conversation import get_conversation_service
from app.dependencies.llm import get_llm_provider
from app.dependencies.rag import get_context_builder

from app.services.streaming_chat_service import (
    StreamingChatService,
)


def get_streaming_service(
    context_builder=Depends(get_context_builder),
    conversations=Depends(get_conversation_service),
    llm_provider=Depends(get_llm_provider),
):
    return StreamingChatService(
        context_builder,
        conversations,
        llm_provider,
    )