from app.agents.state import AgentState


def route(state):
    return state["decision"]


def route_from_supervisor(state: AgentState):

    if state.get("done"):
        return "responder"

    pending_agents = state.get(
        "pending_agents",
        [],
    )

    if pending_agents:
        return pending_agents[0]

    return "responder"