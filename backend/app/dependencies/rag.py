from fastapi import Depends
from app.dependencies.agent import get_agent_graph
from app.services.rag_service import RAGService
from app.dependencies.conversation import get_conversation_service


def get_rag_service(
    graph=Depends(get_agent_graph),
    conversation_service=Depends(get_conversation_service),
):
    return RAGService(
        graph =graph,
        conversation_service = conversation_service
    )