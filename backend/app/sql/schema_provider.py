class SchemaProvider:

    def __init__(self):
        ...

    def get_schema(self) -> str:
        return """
        Table: documents

        Columns:
        - id
        - owner_id
        - original_filename
        - storage_filename
        - storage_path
        - mime_type
        - file_size
        - status
        - created_at
        """