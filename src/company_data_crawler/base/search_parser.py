"""Search-response parser contract: raw results -> ISearchResponse list."""

from abc import ABC, abstractmethod
from typing import Any

from company_data_crawler.interfaces.search_response import ISearchResponse


class SearchResponseParser(ABC):
    """Converts a source-specific search payload into suggestions.

    Pure function of the response body: no I/O, skips entries that
    lack the required name/slug fields instead of failing the batch.
    """

    @abstractmethod
    def parse(self, data: dict[Any, Any]) -> list[ISearchResponse]:
        """Parse raw search results into suggestions.

        Args:
            data: Decoded search payload from the matching
                :class:`CompanyNameScraper`.

        Returns:
            One :class:`ISearchResponse` per usable hit (possibly empty).

        Raises:
            ValueError: If the payload is not the expected shape (e.g.
                not a JSON object, or carries API-level ``errors``).
        """
        pass
