import json


class CraftScrapingUtils:
    """Craft.co request builders: GraphQL endpoint, headers, payload, page URLs."""

    @staticmethod
    def get_search_query_url() -> str:
        """Return the Craft GraphQL endpoint used for name search."""
        return "https://craft.co/graphql"

    @staticmethod
    def prepare_search_query_headers() -> dict[str, str]:
        """Return browser-like headers for the GraphQL search request (same-origin CORS + Chrome UA)."""
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.8",
            "content-type": "application/json",
            "origin": "https://craft.co",
            "priority": "u=1, i",
            "referer": "https://craft.co/amazon",
            "sec-ch-ua": '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }
        return headers

    @staticmethod
    def prepare_search_query_payload(query: str) -> str:
        """Build the ``UniversalSearch`` GraphQL envelope for ``query``.

        Args:
            query: Free-text company name.

        Returns:
            JSON-encoded GraphQL request body (operation + fragments).
        """
        return json.dumps(
            {
                "operationName": "UniversalSearch",
                "variables": {"query": query},
                "query": "query UniversalSearch($query: String\u0021) { universalSearch(query: $query) { ...UniversalSearchResult __typename }}fragment UniversalSearchResult on SearchSuggestion { company { ...CompanyWithLogo __typename } name type url __typename}fragment CompanyWithLogo on Company { id slug displayName logo { id url __typename } __typename}",
            }
        )

    @staticmethod
    def build_craft_page_url(query: str = "google") -> str:
        """Build a Craft search landing URL.

        Used as the Selenium entry page whose search box is driven to
        capture the GraphQL response.

        Args:
            query: Slug appended to ``https://craft.co/``.
        """
        return f"https://craft.co/{query}"
