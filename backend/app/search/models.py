from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = Field(default="")


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult] = Field(default_factory=list)