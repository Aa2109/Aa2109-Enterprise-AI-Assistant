from abc import ABC, abstractmethod

from app.search.models import SearchResponse


class SearchProvider(ABC):

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> SearchResponse:
        raise NotImplementedError