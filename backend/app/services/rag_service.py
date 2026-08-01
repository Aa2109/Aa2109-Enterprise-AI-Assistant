from app.llm.base import LLMProvider
from app.prompts.rag import (
    RAG_SYSTEM_PROMPT,
    build_rag_user_prompt,
)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SourceChunk,
)
from app.schemas.search import SemanticSearchRequest
from app.services.retrieval_service import RetrievalService


class RAGService:

    def __init__(
        self,
        # retrieval_service,
        llm_provider,
        context_builder,
    ):
        # self.retrieval_service = retrieval_service
        self.llm_provider = llm_provider
        self.context_builder = context_builder

    def answer(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        system_prompt, user_prompt, retrieval_result = (
            self.context_builder.build(
                history=[],
                request=request,
            )
        )

        answer = self.llm_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return ChatResponse(
            answer=answer,
            sources=[
                SourceChunk(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    chunk_index=hit.chunk_index,
                    content=hit.content,
                    score=hit.score,
                )
                for hit in retrieval_result.results
            ],
        )
    