import asyncio
from typing import Any

from app.tools.base import BaseTool
from app.tools.schemas import WebSearchInput
from app.search.provider import SearchProvider


class WebSearchTool(BaseTool):

    def __init__(
        self,
        provider: SearchProvider,
    ):
        self.provider = provider

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Searches the public web for current or external "
            "information."
        )

    def execute(
        self,
        arguments: dict[str, Any],
    ) -> Any:

        validated = WebSearchInput(
            **arguments
        )

        response = asyncio.run(
            self.provider.search(
                query=validated.query,
                max_results=validated.max_results,
            )
        )

        return {
            "query": response.query,
            "results": [
                result.model_dump()
                for result in response.results
            ],
        }