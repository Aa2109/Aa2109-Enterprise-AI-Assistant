from app.prompts.rag import RAG_SYSTEM_PROMPT
from app.prompts.rag import build_rag_user_prompt


class ResponderNode:

    def __init__(self, llm, context_builder):

        self.llm = llm

        self.context_builder = context_builder

    def __call__(self, state):

        system_prompt, user_prompt, _ = self.context_builder.build(

            history=state["history"],

            request=state,
        )

        answer = self.llm.generate(

            system_prompt=system_prompt,

            user_prompt=user_prompt,
        )

        state["answer"] = answer

        return state