from functools import lru_cache

from fastapi import Depends

from app.agents.graph import build_graph

from app.dependencies.planner import get_planner
from app.dependencies.retriever import get_retriever
from app.dependencies.responder import get_responder
from app.dependencies.clarify import get_clarify
from app.dependencies.tool_executor import get_tool_executor_node

# @lru_cache
def get_agent_graph(
    planner=Depends(get_planner),
    retriever=Depends(get_retriever),
    responder=Depends(get_responder),
    clarify=Depends(get_clarify),
    tool_executor_node=Depends(get_tool_executor_node),
):
    return build_graph(
        planner,
        retriever,
        responder,
        clarify,
        tool_executor_node,
    )