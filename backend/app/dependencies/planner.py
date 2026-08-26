from fastapi import Depends

from app.agents.nodes.planner import PlannerNode
from app.dependencies.llm import get_llm_provider


def get_planner(
    llm=Depends(get_llm_provider),
):
    return PlannerNode(llm)