from app.core.enums.message import MessageRole
from app.streaming.event import StreamEvent
from app.streaming.formatter import sse


class StreamingChatService:

    def __init__(
        self,
        context_builder,
        conversation_service,
        llm_provider,
    ):
        self.context_builder = context_builder
        self.conversations = conversation_service
        self.llm = llm_provider

    def stream(self, request):

        self.conversations.add_message(
            request.conversation_id,
            role=MessageRole.USER,
            content=request.query,
        )

        history = self.conversations.history(
            request.conversation_id,
        )

        system_prompt, user_prompt, _ = (
            self.context_builder.build(
                history=history,
                request=request,
            )
        )

        yield sse(StreamEvent.START, {})

        answer_parts = []

        try:

            for token in self.llm.stream(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            ):

                if not token:
                    continue

                answer_parts.append(token)

                yield sse(
                    StreamEvent.TOKEN,
                    token,
                )

            answer = "".join(answer_parts)

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
        # finally:
        #   yield sse(StreamEvent.DONE, {})