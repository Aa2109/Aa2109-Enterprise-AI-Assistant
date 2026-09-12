from uuid import UUID, uuid4

from fastapi import HTTPException, status as http_status

from app.core.concurrency import agent_execution_slot
from app.core.enums.message import MessageRole
from app.security.models import UserContext
from app.security.prompt_guard import validate_user_prompt
from app.streaming.event import StreamEvent
from app.streaming.formatter import sse


class StreamingChatService:

    def __init__(
        self,
        graph,
        conversation_service,
    ):
        self.graph = graph
        self.conversations = conversation_service

    def stream(
        self,
        request,
        user: UserContext,
    ):

        # --------------------------------------------------
        # Prompt guard — validate the user prompt before any
        # conversation writes or LLM work.
        # --------------------------------------------------

        try:
            validate_user_prompt(request.query)
        except ValueError as exc:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        self.conversations.add_message(
            request.conversation_id,
            role=MessageRole.USER,
            content=request.query,
        )

        history = self.conversations.history(
            request.conversation_id,
        )

        serializable_history = [
            {
                "role": message.role.value,
                "content": message.content,
            }
            for message in history
        ]

        state = {
            "question": request.query,
            "conversation_id": request.conversation_id,
            # Authoritative owner: the authenticated token wins.
            "owner_id": UUID(user.user_id),
            "document_id": request.document_id,
            "limit": request.limit,
            "history": serializable_history,
            "user_context": user,

            # PR-28 agent/token safeguards
            "agent_step": 0,
            "tool_call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "token_budget_exceeded": False,
        }

        yield sse(StreamEvent.START, {})

        answer = []

        # LangGraph thread configuration. The compiled graph carries a
        # checkpointer (for the HITL approval interrupt/resume flow), which
        # requires a thread_id on every invocation. Mint a fresh run id per
        # turn so each request gets an isolated checkpoint, mirroring
        # RAGService.
        run_id = str(uuid4())
        config = {
            "configurable": {
                "thread_id": run_id,
            }
        }

        try:

            with agent_execution_slot():

                result = self.graph.invoke(state, config=config)

            answer = result["answer"]

            yield sse(
                StreamEvent.TOKEN,
                answer,
            )

            self.conversations.add_message(
                request.conversation_id,
                role=MessageRole.ASSISTANT,
                content=answer,
            )

            yield sse(
                StreamEvent.DONE,
                {},
            )

        except Exception as exc:

            yield sse(
                StreamEvent.ERROR,
                str(exc),
            )