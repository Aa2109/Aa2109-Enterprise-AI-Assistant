from typing import Any

from app.tools.base import BaseTool
from app.prompts.sql import (
    SQL_SYSTEM_PROMPT,
    build_sql_user_prompt,
)
from app.schemas.sql import SQLGeneration
from app.sql.schema_provider import SchemaProvider
from app.sql.validator import SQLValidator
from app.sql.executor import SQLExecutor


class SQLTool(BaseTool):

    def __init__(
        self,
        llm,
        schema_provider: SchemaProvider,
        validator: SQLValidator,
        executor: SQLExecutor,
    ):
        self.llm = llm
        self.schema_provider = schema_provider
        self.validator = validator
        self.executor = executor

    @property
    def name(self) -> str:
        return "sql"

    @property
    def description(self) -> str:
        return (
            "Safely queries approved application data "
            "using read-only SQL."
        )

    def execute(
        self,
        arguments: dict[str, Any],
    ) -> Any:

        question = arguments.get("question")

        if not question:
            raise ValueError(
                "SQL tool requires a question"
            )

        schema = self.schema_provider.get_schema()

        prompt = build_sql_user_prompt(
            question=question,
            schema=schema,
        )

        generated = self.llm.generate_structured(
            system_prompt=SQL_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=SQLGeneration,
        )

        sql = generated.sql

        self.validator.validate(sql)

        return self.executor.execute(sql)