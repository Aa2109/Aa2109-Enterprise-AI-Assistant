from fastapi import Depends

from app.dependencies.agent import get_agent_graph
from app.dependencies.conversation import get_conversation_service
from app.services.streaming_chat_service import StreamingChatService


def get_streaming_service(
    graph=Depends(get_agent_graph),
    conversations=Depends(get_conversation_service),
):
    return StreamingChatService(
        graph,
        conversations,
    )