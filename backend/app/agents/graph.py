from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.state import AgentState
from app.agents.routing import route_from_supervisor


checkpointer = InMemorySaver()


def build_graph(
    responder,
    memory_retriever_node,
    memory_extractor_node,
    supervisor,
    rag_agent,
    research_agent,
    data_agent,
):
    """Build the LangGraph for the supervisor + specialists flow.

    PR-30 — the legacy planner/tool_executor/clarify/retriever nodes are
    no longer wired in. Those files remain in ``app/agents/nodes/`` for
    reference but the supervisor path is the only execution flow:

        START → memory_retriever → supervisor
               → [rag | research | data] → supervisor (loop)
               → responder → memory_extractor → END
    """

    graph = StateGraph(
        AgentState
    )

    # ================================================
    # Memory
    # ================================================

    graph.add_node(
        "memory_retriever",
        memory_retriever_node,
    )

    graph.add_node(
        "memory_extractor",
        memory_extractor_node,
    )

    # ================================================
    # Supervisor + specialists
    # ================================================

    graph.add_node(
        "supervisor",
        supervisor,
    )

    graph.add_node(
        "rag",
        rag_agent,
    )

    graph.add_node(
        "research",
        research_agent,
    )

    graph.add_node(
        "data",
        data_agent,
    )

    # ================================================
    # Final response
    # ================================================

    graph.add_node(
        "responder",
        responder,
    )

    # ================================================
    # Edges
    # ================================================

    graph.add_edge(
        START,
        "memory_retriever",
    )

    graph.add_edge(
        "memory_retriever",
        "supervisor",
    )

    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "rag": "rag",
            "research": "research",
            "data": "data",
            "responder": "responder",
        },
    )

    graph.add_edge(
        "rag",
        "supervisor",
    )

    graph.add_edge(
        "research",
        "supervisor",
    )

    graph.add_edge(
        "data",
        "supervisor",
    )

    graph.add_edge(
        "responder",
        "memory_extractor",
    )

    graph.add_edge(
        "memory_extractor",
        END,
    )

    return graph.compile(
        checkpointer=checkpointer
    )