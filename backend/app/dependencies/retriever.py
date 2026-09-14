from fastapi import Depends

from app.agents.nodes.retriever import RetrieverNode
from app.dependencies.retrieval import get_retrieval_service


def get_retriever(
    retrieval_service=Depends(get_retrieval_service),
):
    return RetrieverNode(retrieval_service)