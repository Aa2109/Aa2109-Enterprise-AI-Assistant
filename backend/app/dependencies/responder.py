from fastapi import Depends

from app.agents.nodes.responder import ResponderNode
from app.dependencies.llm import get_llm_provider
from app.dependencies.context_builder import get_context_builder


def get_responder(
    llm=Depends(get_llm_provider),
    context_builder=Depends(get_context_builder),
):
    return ResponderNode(
        llm,
        context_builder,
    )