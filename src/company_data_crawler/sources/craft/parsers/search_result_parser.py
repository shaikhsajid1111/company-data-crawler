import json

from company_data_crawler.base.search_parser import SearchResponseParser
from company_data_crawler.global_utils.uri_utils import UriUtils
from company_data_crawler.interfaces.search_response import ISearchResponse
from company_data_crawler.logger import get_logger

logger = get_logger(__name__)


class CraftSearchParser(SearchResponseParser):
    """Parse Craft's ``UniversalSearch`` GraphQL payload into suggestions."""

    def parse(self, data) -> list[ISearchResponse]:
        """Convert the ``universalSearch`` suggestion list to ISearchResponse entries.

        Builds each canonical URL from the hit's ``slug`` and tolerates
        missing logos.

        Args:
            data: Raw GraphQL response body as text.

        Returns:
            One :class:`ISearchResponse` per suggestion.

        Raises:
            ValueError: On non-object JSON, API-level ``errors``, or a
                malformed ``universalSearch`` value.
            Exception: JSON decode failures (after logging).
        """
        try:
            dict_data = json.loads(data)
            if not isinstance(dict_data, dict):
                raise ValueError("Search response must be a JSON object")

            errors = dict_data.get("errors")
            if errors:
                raise ValueError(f"Craft GraphQL returned errors: {errors}")

            company_data = dict_data.get("data", {}).get("universalSearch") or []
            if not isinstance(company_data, list):
                raise ValueError("Search response has an invalid universalSearch value")

            search_responses: list[ISearchResponse] = []
            for search_data in company_data:
                company_search_data = search_data.get("company", {})
                if not company_search_data:
                    continue
                company_name = company_search_data.get("displayName")
                slug = company_search_data.get("slug")
                source_url = UriUtils.build_craft_source_page_url(slug)
                logo_url = (company_search_data.get("logo") or {}).get("url")
                search_response_data = ISearchResponse(
                    company_name=company_name,
                    source_url=source_url,
                    logo_url=logo_url,
                    slug=slug,
                )
                search_responses.append(search_response_data)
            return search_responses

        except Exception as ex:
            logger.exception(f"Error while parsing search response: {ex}")
            raise
