from collections.abc import Iterable
from typing import Optional

from company_data_crawler.base.scraper import UrlScraper
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger

logger = get_logger("URL scraper chain")


class CraftUrlScraperChain(UrlScraper):
    """Try URL scrapers in order until one returns a page.

    For Craft, this tries HTTP first, then falls back to Selenium.
    """

    def __init__(self, scrapers: Iterable[UrlScraper]):
        """Chain scrapers tried in order (HTTP first, Selenium fallback).

        Args:
            scrapers: Non-empty sequence of :class:`UrlScraper`.

        Raises:
            ValueError: If ``scrapers`` is empty.
        """
        self.scrapers = tuple(scrapers)
        if not self.scrapers:
            raise ValueError("UrlScraperChain requires at least one scraper")

    def build_proxies(self, proxy: str | None):
        """No-op: proxy handling is delegated to each chained scraper."""
        return None

    def scrape(self, url: str, config: ICrawlerConfig | None = None) -> str:
        """Return the first successful scraper's payload for ``url``.

        Each failure is logged with traceback and the next scraper is
        tried; when all fail, the *last* error is re-raised.

        Args:
            url: Company page URL.
            config: Forwarded to every chained scraper.

        Returns:
            Raw page payload from the first scraper that succeeds.

        Raises:
            Exception: The last scraper's error, if none succeeded.
        """
        last_error: Exception | None = None

        for scraper in self.scrapers:
            try:
                logger.info("Trying %s for %s", type(scraper).__name__, url)
                return scraper.scrape(url, config)
            except Exception as ex:
                last_error = ex
                logger.warning(
                    "%s failed for %s; trying the next scraper",
                    type(scraper).__name__,
                    url,
                    exc_info=True,
                )

        assert last_error is not None
        raise last_error
