"""LEGACY — retained for reference, not wired into the graph since PR-30.

The supervisor + specialists path is the only execution flow.
"""

class ClarifyNode:

    def __call__(self, state):

        state["answer"] = (
            "Could you clarify your question?"
        )

        return state