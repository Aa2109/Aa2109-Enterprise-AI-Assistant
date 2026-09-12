from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.state import AgentState
from app.agents.routing import route_from_supervisor


checkpointer = InMemorySaver()


def build_graph(
    planner,
    retriever,
    responder,
    clarify,
    tool_executor_node,
    memory_retriever_node,
    memory_extractor_node,
    supervisor,
    rag_agent,
    research_agent,
    data_agent,
):

    graph = StateGraph(
        AgentState
    )

    # ================================================
    # Existing nodes
    # ================================================

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

    graph.add_node(
        "tool_executor",
        tool_executor_node,
    )

    graph.add_node(
        "memory_retriever",
        memory_retriever_node,
    )

    graph.add_node(
        "memory_extractor",
        memory_extractor_node,
    )

    # ================================================
    # PR-26 supervisor + specialists
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
    # PR-26 execution path / main flow
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
            # "supervisor": "supervisor",
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

    # ================================================
    # Existing finalization
    # ================================================

    graph.add_edge(
        "responder",
        "memory_extractor",
    )

    graph.add_edge(
        "memory_extractor",
        END,
    )

    # ================================================
    # Old planner path
    # Keep temporarily while migrating.
    # ================================================
   
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

    graph.add_edge(
        "retriever",
        "planner",
    )

    graph.add_edge(
        "tool_executor",
        "planner",
    )

    graph.add_edge(
        "clarify",
        END,
    )

    return graph.compile(
        checkpointer=checkpointer
    )