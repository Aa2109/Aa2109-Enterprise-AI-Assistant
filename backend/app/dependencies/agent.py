from functools import lru_cache

from fastapi import Depends

from app.agents.graph import build_graph

from app.dependencies.planner import get_planner
from app.dependencies.retriever import get_retriever
from app.dependencies.responder import get_responder
from app.dependencies.clarify import get_clarify
from app.dependencies.tool_executor import get_tool_executor_node
from app.dependencies.memory import(
get_memory_retriever_node,
get_memory_extractor_node,
)
from app.dependencies.specialised_agents import(
get_supervisor, 
get_rag_agent,
get_research_agent,
get_data_agent
)

# @lru_cache
def get_agent_graph(
    planner=Depends(get_planner),
    retriever=Depends(get_retriever),
    responder=Depends(get_responder),
    clarify=Depends(get_clarify),
    tool_executor_node=Depends(get_tool_executor_node),
    memory_retriever_node=Depends(get_memory_retriever_node),
    memory_extractor_node=Depends(get_memory_extractor_node),
    supervisor=Depends(get_supervisor),
    rag_agent=Depends(get_rag_agent),
    research_agent=Depends(get_research_agent),
    data_agent=Depends(get_data_agent),
):
    return build_graph(
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
        data_agent
    )