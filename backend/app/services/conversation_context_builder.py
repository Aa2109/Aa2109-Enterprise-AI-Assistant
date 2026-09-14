from app.core.config import settings
from app.prompts.rag import (
    RAG_SYSTEM_PROMPT,
    build_rag_user_prompt,
)

class ConversationContextBuilder:

    def build(
        self,
        history,
        request,
        retrieved_chunks,
    ):
        context_blocks = [
            f"[Chunk {hit.chunk_index} | Score: {hit.score:.2f}]\n{hit.content}"
            for hit in retrieved_chunks
        ]

        context = (
            "\n\n".join(context_blocks)
            if context_blocks
            else "No relevant context found."
        )

        # PR-28 — never hand the whole retrieval dump to the LLM.
        # Cap the context at MAX_CONTEXT_CHARS; token-aware truncation
        # is the eventual improvement.
        if settings.MAX_CONTEXT_CHARS > 0 and len(
            context,
        ) > settings.MAX_CONTEXT_CHARS:
            context = context[: settings.MAX_CONTEXT_CHARS]
        
        history_text = "\n".join(
            f"{m.role.value}: {m.content}"
            for m in history[-10:]
        )

        user_prompt = build_rag_user_prompt(
            question=request["question"],
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
            retrieved_chunks,
        )