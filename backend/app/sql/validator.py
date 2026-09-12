import sqlglot
from sqlglot import exp


class SQLValidator:

    ALLOWED_TABLES = {
        "documents",
        "chunks",
    }

    ALLOWED_SCHEMAS = {
        "public",
    }

    def validate(self, sql: str) -> None:

        if not sql or not sql.strip():
            raise ValueError("SQL query is empty")

        try:
            statements = sqlglot.parse(
                sql,
                dialect="postgres",
            )
        except Exception as exc:
            raise ValueError(
                f"Invalid SQL syntax: {exc}"
            ) from exc

        if len(statements) != 1:
            raise ValueError(
                "Only one SQL statement is allowed"
            )

        statement = statements[0]

        # Only SELECT is allowed
        if not isinstance(statement, exp.Select):
            raise ValueError(
                "Only SELECT queries are allowed"
            )

        # Check tables
        for table in statement.find_all(exp.Table):

            table_name = table.name.lower()

            if table_name not in self.ALLOWED_TABLES:
                raise ValueError(
                    f"Table '{table_name}' is not allowed"
                )

            if table.db:
                schema_name = table.db.lower()

                if schema_name not in self.ALLOWED_SCHEMAS:
                    raise ValueError(
                        f"Schema '{schema_name}' is not allowed"
                    )