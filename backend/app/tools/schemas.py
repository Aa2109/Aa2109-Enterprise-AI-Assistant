from pydantic import BaseModel, Field


class CalculatorInput(BaseModel):
    expression: str = Field(
        ...,
        description="Mathematical expression to calculate."
    )


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
    )