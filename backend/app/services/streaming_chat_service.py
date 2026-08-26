from app.core.enums.message import MessageRole
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

    def stream(self, request):

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
            "owner_id": request.owner_id,
            "document_id": request.document_id,
            "limit": request.limit,
            "history": serializable_history,
        }

        yield sse(StreamEvent.START, {})

        answer = []

        try:

            result = self.graph.invoke(state)

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

        except Exception as exc:

            yield sse(
                StreamEvent.ERROR,
                str(exc),
            )