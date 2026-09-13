from curl_cffi import requests

from company_data_crawler.base.scraper import CompanyNameScraper
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger
from company_data_crawler.sources.craft.utils import CraftScrapingUtils

logger = get_logger(__name__)


class CraftCompanySearchCrawler(CompanyNameScraper):
    """Name search via Craft's GraphQL ``UniversalSearch`` endpoint (HTTP POST)."""

    def build_proxies(self, proxy: str | None) -> dict | None:
        """Map proxy config to curl-cffi's ``{"http": ..., "https": ...}`` form, or ``None`` when unset."""
        if not proxy:
            return None
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    def scrape(self, query: str, config: ICrawlerConfig | None = None) -> str:
        """POST the ``UniversalSearch`` query and return the raw response.

        Args:
            query: Free-text company name.
            config: Proxy/timeout settings (Chrome impersonation always on).

        Returns:
            Raw GraphQL response body as text.

        Raises:
            Exception: Transport/HTTP errors (after logging).
        """
        try:
            headers = CraftScrapingUtils.prepare_search_query_headers()
            payload = CraftScrapingUtils.prepare_search_query_payload(query)
            url = CraftScrapingUtils.get_search_query_url()
            proxy: str | None = config.proxy if config else None
            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=payload,
                impersonate="chrome",
                proxies=self.build_proxies(proxy),
                timeout=config.request_timeout if config else 30.0,
            )
            response.raise_for_status()
            return response.text
        except Exception as ex:
            logger.exception(f"Error while trying to fetch company by name: {ex}")
            raise
