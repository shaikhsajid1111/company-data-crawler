import os
from typing import Optional

from company_data_crawler.base.parser import Parser
from company_data_crawler.base.scraper import UrlScraper
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger
from company_data_crawler.models.company_data import CompanyData
from company_data_crawler.storage.persistent_disk_cache import DiskCache
from company_data_crawler.utils.general_utils import GeneralUtils

logger = get_logger("Scraping Orchestrator")


class CompanyPageScrapingService:
    """Source-agnostic service for scraping and parsing company pages.

    Each source provides its own UrlScraper and Parser implementations,
    making this service fully source-agnostic.
    """

    def __init__(
        self,
        page_parser: Parser,
        url_scraper: UrlScraper,
        cache_dir: str | None = None,
    ):
        """Wire a source's fetch + parse halves to a CompanyData cache.

        Args:
            page_parser: Turns the fetched payload into CompanyData.
            url_scraper: Fetches the raw page (often a fallback chain).
            cache_dir: Base dir for the ``CompanyData`` disk cache;
                defaults to the current working directory.
        """
        self.url_scraper = url_scraper
        self.page_parser = page_parser
        self._disk_cache = DiskCache(CompanyData, cache_dir or os.getcwd())

    def fetch_page(self, url: str, config: ICrawlerConfig | None = None) -> str:
        """Fetch the raw page for ``url`` via the source's scraper.

        Logs and re-raises transport errors unchanged so chains and
        callers can react to them.

        Args:
            url: Company page URL.
            config: Crawl settings forwarded to the scraper.

        Returns:
            Raw page payload.

        Raises:
            Exception: Whatever the underlying scraper raised.
        """
        try:
            return self.url_scraper.scrape(url, config)
        except Exception:
            logger.exception("Error while fetching page: %s", url)
            raise

    def parse_page(self, page_data: str) -> CompanyData | None:
        """Parse a previously fetched payload.

        Args:
            page_data: Raw page content as returned by :meth:`fetch_page`.

        Returns:
            The parsed record (or ``None``), re-raising parse errors
            after logging.

        Raises:
            Exception: Whatever the underlying parser raised.
        """
        try:
            return self.page_parser.parse(page_data)
        except Exception:
            logger.exception("Error while parsing page")
            raise

    def scrape_company_page(
        self, url: str, config: ICrawlerConfig | None = None
    ) -> CompanyData | None:
        """Return cached CompanyData for ``url``, else scrape → parse → cache.

        Honors ``force_rescrape`` (bypass cache) and stamps fresh
        records with a TTL derived from
        ``company_cache_expiry_time_days``.

        Args:
            url: Company page URL (also the cache key).
            config: Crawl settings; defaults are used when omitted.

        Returns:
            The company record, or ``None`` when unparseable.

        Raises:
            Exception: Fetch/parse failures after logging.
        """
        crawler_config = config if config is not None else ICrawlerConfig()
        try:
            if not crawler_config.force_rescrape:
                cached_data = self._disk_cache.get(url)
                if cached_data:
                    return cached_data

            page_data = self.fetch_page(url, crawler_config)
            parsed_page = self.page_parser.parse(page_data)
            self._disk_cache.set(
                url,
                parsed_page,
                GeneralUtils.generate_time_from_now(
                    crawler_config.company_cache_expiry_time_days
                ).timestamp(),
            )
            return parsed_page
        except Exception:
            logger.exception("Error while processing page: %s", url)
            raise
