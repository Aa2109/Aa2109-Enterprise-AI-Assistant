from sqlalchemy import text


class SQLExecutor:

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def execute(self, sql: str):

        with self.session_factory() as session:

            result = session.execute(
                text(sql)
            )

            columns = list(result.keys())

            rows = [
                list(row)
                for row in result.fetchmany(100)
            ]

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }