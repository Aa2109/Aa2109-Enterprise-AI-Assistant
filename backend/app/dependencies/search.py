from fastapi import Depends

from app.search.provider import SearchProvider
from app.search.tavily_provider import TavilySearchProvider


# def get_search_provider() -> SearchProvider:
    # Read SEARCH_PROVIDER and TAVILY_API_KEY
    # from your application's existing settings/config.
    #
    # Return TavilySearchProvider(...)
    #
    # Do not hard-code the API key.

    # raise NotImplementedError

from app.search.tavily_provider import TavilySearchProvider
from app.core.config import settings

def get_search_provider():
    return TavilySearchProvider(
        api_key=settings.TAVILY_API_KEY,
    )