from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SourceChunk,
)
from app.core.enums.message import MessageRole
from uuid import uuid4


class RAGService:

    def __init__(
        self,
        graph,
        conversation_service,
    ):
        self.graph = graph
        self.conversation_service = conversation_service

    def answer(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        # Validate Conversation
        conversation = self.conversation_service.get(
            request.conversation_id
        )

        if conversation is None:
            raise ValueError(
                f"Conversation not found: "
                f"{request.conversation_id}"
            )

        # 1. Load Conversation history
        history = self.conversation_service.history(
            request.conversation_id
        )

        print(
            "Conversation history:",
            len(history),
        )

        # ==================================================
        # 2. Build graph state
        # ==================================================

        run_id = str(uuid4())
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
            "run_id": run_id, # new added...
            "owner_id": request.owner_id,
            "document_id": request.document_id,
            "limit": request.limit,
            "history": serializable_history,

            # Agent execution state(new added)
            "iteration": 0,
            "tool_call_count": 0,
            "retry_count": 0,
            "tool_executions": [],

            "tool_name": None,
            "tool_arguments": None,
            "tool_result": None,
            "tool_error": None,

            "retrieved_chunks": [],
            "web_results": [],

            "approval_required": False,
            "approval_request_id": None,
            "approval_status": None,


        }

        # ==================================================
        # 3. LangGraph thread configuration
        # ==================================================

        config = {
            "configurable": {
                "thread_id": run_id
            }
        }

        # ==================================================
        # 4. Invoke graph
        # ==================================================

        result = self.graph.invoke(
            state,
            config=config,
        )

        # ==================================================
        # 5. HITL approval interrupt
        # ==================================================

        interrupts = result.get(
            "__interrupt__",
            []
        )

        if interrupts:

            print(
                "[APPROVAL] Graph paused for human approval"
            )

            interrupt_value = None

            first_interrupt = interrupts[0]

            if hasattr(
                first_interrupt,
                "value",
            ):
                interrupt_value = first_interrupt.value
                

            elif isinstance(
                first_interrupt,
                dict,
            ):
                interrupt_value = first_interrupt

            print(
                "[APPROVAL] Interrupt value:",
                interrupt_value,
            )

            approval_id = None

            if isinstance(
                interrupt_value,
                dict,
            ):

                approval_id = interrupt_value.get("approval_id")

            # --------------------------------------------------
            # Save USER message only.
            #
            # Do NOT save an assistant answer because the
            # agent has not completed yet.
            # --------------------------------------------------

            self.conversation_service.add_message(
                conversation_id=request.conversation_id,
                role=MessageRole.USER,
                content=request.query,
            )

            return ChatResponse(
                answer=None,
                sources=[],
                status="approval_required",
                approval_id=approval_id,
            )

        # ==================================================
        # 6. Normal completed execution
        # ==================================================

        retrieved_chunks = result.get(
            "retrieved_chunks",
            [],
        )

        answer = result.get(
            "answer"
        )

        # ==================================================
        # Safety check
        # ==================================================

        if answer is None:

            raise RuntimeError(
                "Agent execution completed without an answer "
                "and without an approval interrupt."
            )

        # ==================================================
        # 7. Save USER message
        # ==================================================

        self.conversation_service.add_message(
            conversation_id=request.conversation_id,
            role=MessageRole.USER,
            content=request.query,
        )

        # ==================================================
        # 8. Save ASSISTANT message
        # ==================================================

        self.conversation_service.add_message(
            conversation_id=request.conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer,
        )

        # ==================================================
        # 9. Return normal response
        # ==================================================

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
                for hit in retrieved_chunks
            ],
            status="completed",
            approval_id=None,
        )

