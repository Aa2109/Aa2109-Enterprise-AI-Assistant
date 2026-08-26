from pydantic import BaseModel, Field


class SQLGeneration(BaseModel):

    sql: str = Field(
        description="A single read-only PostgreSQL SELECT query"
    )