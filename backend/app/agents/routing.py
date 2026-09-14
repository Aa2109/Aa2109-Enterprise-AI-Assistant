from app.agents.state import AgentState


def route(state):
    return state["decision"]


def route_from_supervisor(state: AgentState):

    # PR-30 — pending specialists must always run before the responder,
    # even if the router LLM returned done=true alongside a non-empty
    # agent list. The supervisor already clears ``pending_agents`` every
    # time it finalizes, so a non-empty pending list is the ground truth:
    # the next specialist to execute is always pending_agents[0].
    #
    # Checking ``done`` first would let a single misbehaving LLM turn
    # (done=true, agents=[rag, research]) into a response with no
    # evidence gathered at all — exactly the hallucination path the
    # SynthesisPolicy is meant to close.
    pending_agents = state.get(
        "pending_agents",
        [],
    )

    if pending_agents:
        return pending_agents[0]

    return "responder"