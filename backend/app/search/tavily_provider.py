from tavily import TavilyClient

from app.search.provider import SearchProvider
from app.search.models import SearchResponse, SearchResult


class TavilySearchProvider(SearchProvider):

    def __init__(self, api_key: str):
        self.client = TavilyClient(
            api_key=api_key
        )

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> SearchResponse:

        response = self.client.search(
            query=query,
            max_results=max_results,
        )

        results = []

        for item in response.get("results", []):

            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                )
            )

        return SearchResponse(
            query=query,
            results=results,
        )