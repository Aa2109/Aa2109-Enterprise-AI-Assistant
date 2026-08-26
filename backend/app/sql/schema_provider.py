class SchemaProvider:

    def __init__(self):
        ...

    def get_schema(self) -> str:
        return """
        Table: documents

        Columns:
        - id
        - filename
        - owner_id
        - status
        - created_at
        """