from fastapi import Depends

from app.db.database import SessionLocal
from app.tools.registry import ToolRegistry
from app.tools.implementations.calculator import CalculatorTool
from app.tools.implementations.sql import SQLTool

from app.dependencies.llm import get_llm_provider
from app.sql.schema_provider import SchemaProvider
from app.sql.validator import SQLValidator
from app.sql.executor import SQLExecutor

from app.tools.implementations.web_search import WebSearchTool
from app.tools.implementations.support_ticket import (
    CreateSupportTicketTool,
)

from app.dependencies.search import get_search_provider


def get_tool_registry(
    llm=Depends(get_llm_provider),
    search_provider=Depends(get_search_provider),
):
    schema_provider = SchemaProvider()
    validator = SQLValidator()
    executor = SQLExecutor(session_factory=SessionLocal)

    sql_tool = SQLTool(
        llm=llm,
        schema_provider=schema_provider,
        validator=validator,
        executor=executor,
    )

    web_search_tool = WebSearchTool(provider=search_provider,)

    return ToolRegistry(
        tools=[
            CalculatorTool(),
            sql_tool,
            web_search_tool,
            CreateSupportTicketTool(),

        ]
    )