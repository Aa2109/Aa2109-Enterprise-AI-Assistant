from app.services.conversation_context_builder import ConversationContextBuilder
from fastapi import Depends

from app.dependencies.retrieval import get_retrieval_service
from app.dependencies.llm import get_llm_provider
from app.services.rag_service import RAGService

def get_context_builder(
    retrieval_service=Depends(get_retrieval_service),
):
    return ConversationContextBuilder(
        retrieval_service,
    )


def get_rag_service(
    llm_provider=Depends(get_llm_provider),
    context_builder=Depends(get_context_builder),
):
    return RAGService(
        llm_provider,
        context_builder,
    )