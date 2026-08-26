from langgraph.graph import StateGraph, START, END

from langgraph.checkpoint.memory import InMemorySaver

from app.agents.state import AgentState

checkpointer = InMemorySaver()

def build_graph(
    planner,
    retriever,
    responder,
    clarify,
    tool_executor_node,
    ):

    graph = StateGraph(AgentState)

    graph.add_node("planner",planner, )
    graph.add_node("retriever",retriever, )
    graph.add_node("responder",responder, )
    graph.add_node("clarify",clarify, )
    graph.add_node("tool_executor", tool_executor_node)
    

    graph.add_edge(START,"planner",)

    graph.add_conditional_edges(
        "planner",
        lambda state: state["decision"],
        {
            "RAG": "retriever",
            "DIRECT": "responder",
            "TOOL": "tool_executor",
            "CLARIFY": "clarify",
            "UNSUPPORTED": "responder",
            "FINAL": "responder",
        },
    )

    graph.add_edge("retriever","planner", )
    graph.add_edge("tool_executor", "planner")
    graph.add_edge( "responder",END, )
    graph.add_edge("clarify",END, )

    return graph.compile(
        checkpointer=checkpointer
    )