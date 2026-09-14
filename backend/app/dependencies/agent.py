from functools import lru_cache

from fastapi import Depends

from app.agents.graph import build_graph

from app.dependencies.responder import get_responder
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
    responder=Depends(get_responder),
    memory_retriever_node=Depends(get_memory_retriever_node),
    memory_extractor_node=Depends(get_memory_extractor_node),
    supervisor=Depends(get_supervisor),
    rag_agent=Depends(get_rag_agent),
    research_agent=Depends(get_research_agent),
    data_agent=Depends(get_data_agent),
):
    return build_graph(
        responder,
        memory_retriever_node,
        memory_extractor_node,
        supervisor,
        rag_agent,
        research_agent,
        data_agent
    )