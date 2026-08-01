class ClarifyNode:

    def __call__(self, state):

        state["answer"] = (
            "Could you clarify your question?"
        )

        return state