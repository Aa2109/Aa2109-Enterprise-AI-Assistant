from app.sql.schema_provider import SchemaProvider


def test_document_schema_uses_model_column_names():
    schema = SchemaProvider().get_schema()

    assert "- original_filename" in schema
    assert "- filename" not in schema