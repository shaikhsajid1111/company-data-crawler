import json

from company_data_crawler.base.search_parser import SearchResponseParser
from company_data_crawler.interfaces.search_response import ISearchResponse
from company_data_crawler.logger import get_logger

logger = get_logger(__name__)


class OwlerSearchParser(SearchResponseParser):
    """Parser for Owler search API responses."""

    def parse(self, data) -> list[ISearchResponse]:
        """Convert the ``results`` array into ISearchResponse entries.

        Uses each hit's ``name`` + ``teamName`` slug, preferring the
        ``seoFriendlyCompanyProfileUrl`` when present and otherwise
        building ``https://www.owler.com/company/<slug>``. Hits missing
        a name or slug are skipped.

        Args:
            data: Raw search API response body as text.

        Returns:
            One :class:`ISearchResponse` per usable hit (maybe empty).

        Raises:
            ValueError: When the payload is not a JSON object.
            Exception: JSON decode failures (after logging).
        """
        try:
            dict_data = json.loads(data)
            if not isinstance(dict_data, dict):
                raise ValueError("Search response must be a JSON object")

            search_responses: list[ISearchResponse] = []

            # Owler search API returns results in the "results" array
            results = dict_data.get("results", [])

            for company_data in results:
                company_name = company_data.get("name", "")
                slug = company_data.get("teamName") or ""
                if not company_name or not slug:
                    continue

                # Use seoFriendlyCompanyProfileUrl if available, otherwise build from slug
                source_url = company_data.get("seoFriendlyCompanyProfileUrl", "")
                if not source_url:
                    source_url = f"https://www.owler.com/company/{slug}"

                logo_url = company_data.get("logo", "")

                search_response_data = ISearchResponse(
                    company_name=company_name,
                    source_url=source_url,
                    logo_url=logo_url if logo_url else None,
                    slug=slug,
                )
                search_responses.append(search_response_data)

            return search_responses

        except Exception as ex:
            logger.exception(f"Error while parsing Owler search response: {ex}")
            raise
