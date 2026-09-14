from fastapi import Depends

from app.agents.supervisor import Supervisor
from app.agents.specialists.rag_agent import RAGAgent
from app.agents.specialists.research_agent import ResearchAgent
from app.agents.specialists.data_agent import DataAgent

from app.dependencies.llm import get_llm_provider
from app.dependencies.retriever import get_retriever
from app.dependencies.tools import get_tool_registry


def get_supervisor(
    llm=Depends(get_llm_provider),
):
    return Supervisor(
        llm=llm,
    )


def get_rag_agent(
    retriever=Depends(get_retriever),
):
    return RAGAgent(
        retriever=retriever,
    )


def get_research_agent(
    tool_registry=Depends(get_tool_registry),
):
    web_search_tool = tool_registry.get("web_search")

    if web_search_tool is None:
        raise RuntimeError(
            "Web search tool is not registered in ToolRegistry"
        )

    return ResearchAgent(
        web_search_tool=web_search_tool,
    )


def get_data_agent(
    tool_registry=Depends(get_tool_registry),
):
    sql_tool = tool_registry.get("sql")

    if sql_tool is None:
        raise RuntimeError(
            "SQL tool is not registered in ToolRegistry"
        )

    return DataAgent(
        sql_tool=sql_tool,
    )