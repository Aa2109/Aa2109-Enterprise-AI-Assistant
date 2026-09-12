from app.agents.nodes.responder import ResponderNode


class DummyLLM:
    def generate(self, *, system_prompt, user_prompt):
        return "fallback response"


def test_responder_finalizes_supervisor_state_without_planner_decision():
    node = ResponderNode(
        llm=DummyLLM(),
        context_builder=None,
    )

    state = {
        "question": "What is the data?",
        "decision": None,
        "done": True,
        "supervisor_done": True,
    }

    result = node(state)

    assert result["answer"] == "fallback response"