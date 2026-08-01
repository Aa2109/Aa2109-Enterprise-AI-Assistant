from app.prompts.rag import (
    RAG_SYSTEM_PROMPT,
    build_rag_user_prompt,
)
from app.schemas.search import SemanticSearchRequest


class ConversationContextBuilder:

    def __init__(self, retrieval_service):
        self.retrieval_service = retrieval_service

    def build(
        self,
        history,
        request,
    ):

        retrieval_request = SemanticSearchRequest(
            query=request.query,
            limit=request.limit,
            owner_id=request.owner_id,
            document_id=request.document_id,
            score_threshold=None,
        )

        retrieval_result = self.retrieval_service.search(
            retrieval_request
        )

        context_blocks = []

        for hit in retrieval_result.results:
            context_blocks.append(
                f"[Chunk {hit.chunk_index} | Score: {hit.score:.2f}]\n{hit.content}"
            )

        context = (
          "\n\n".join(context_blocks)
          if context_blocks
          else "No relevant context found."
        )

        history_text = "\n".join(
            f"{m.role.value}: {m.content}"
            for m in history[-10:]
        )

        user_prompt = build_rag_user_prompt(
            question=request.query,
            context=context,
        )

        if history_text:
            user_prompt += (
                "\n\nConversation History:\n"
                f"{history_text}"
            )

        return (
            RAG_SYSTEM_PROMPT,
            user_prompt,
            retrieval_result,
        )