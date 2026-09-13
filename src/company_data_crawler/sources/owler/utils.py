class OwlerScrapingUtils:
    """Owler.com request builders: search/page headers and search URL."""

    @staticmethod
    def prepare_search_query_headers() -> dict[str, str]:
        """Return browser-like headers for the ``basicSearchInternal`` API (same-origin CORS + Chrome UA)."""
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9",
            "priority": "u=1, i",
            "referer": "https://www.owler.com/company/google",
            "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Brave";v="152"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Linux",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
        }

        return headers

    @staticmethod
    def prepare_page_headers() -> dict[str, str]:
        """Headers for fetching Owler company pages (mimics real browser)."""
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-GB,en;q=0.6",
            "cache-control": "max-age=0",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Brave";v="152"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
        }

    @staticmethod
    def get_search_query_url(company_name: str):
        """Build the ``basicSearchInternal`` URL for ``company_name``.

        Args:
            company_name: Raw search term interpolated as ``searchTerm``.

        Returns:
            The Owler internal search API URL.
        """
        return f"https://www.owler.com/a/v1/pb/basicSearchInternal?searchTerm={company_name}"
