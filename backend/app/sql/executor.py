from sqlalchemy import text

from app.core.config import settings


class SQLExecutor:

    def __init__(self, session_factory, max_rows: int | None = None):
        self.session_factory = session_factory
        # PR-28 — never let a Data Agent pull the whole table back.
        self.max_rows = (
            max_rows
            if max_rows is not None
            else settings.MAX_QUERY_ROWS
        )

    def execute(self, sql: str):

        with self.session_factory() as session:

            result = session.execute(
                text(sql)
            )

            columns = list(result.keys())

            rows = [
                list(row)
                for row in result.fetchmany(self.max_rows)
            ]

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }