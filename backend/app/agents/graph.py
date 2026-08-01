from langgraph.graph import StateGraph
from langgraph.graph import START
from langgraph.graph import END

from app.agents.state import AgentState


def build_graph(

    planner,

    retriever,

    responder,

    clarify,
):

    graph = StateGraph(AgentState)

    graph.add_node(

        "planner",

        planner,
    )

    graph.add_node(

        "retriever",

        retriever,
    )

    graph.add_node(

        "responder",

        responder,
    )

    graph.add_node(

        "clarify",

        clarify,
    )

    graph.add_edge(

        START,

        "planner",
    )

    graph.add_conditional_edges(

        "planner",

        lambda state: state["decision"],

        {

            "RAG": "retriever",

            "DIRECT": "responder",

            "CLARIFY": "clarify",
        },
    )

    graph.add_edge(

        "retriever",

        "responder",
    )

    graph.add_edge(

        "responder",

        END,
    )

    graph.add_edge(

        "clarify",

        END,
    )

    return graph.compile()