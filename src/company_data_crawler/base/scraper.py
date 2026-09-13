"""Scraper contracts: fetch raw pages / search results (I/O only)."""

from abc import ABC, abstractmethod
from typing import Optional

from company_data_crawler.interfaces.iconfig import ICrawlerConfig


class UrlScraper(ABC):
    """Fetches a company page and returns its raw content.

    Scrapers do transport only — no parsing. A source typically ships
    an HTTP scraper plus a Selenium fallback composed in a chain.
    """

    @abstractmethod
    def build_proxies(self, proxy: str | None) -> dict | None:
        """Translate ``"host:port"`` / ``"user:pass@host:port"`` config into the proxy mapping the underlying HTTP/browser client expects, or ``None`` when no proxy is configured."""
        pass

    @abstractmethod
    def scrape(self, url: str, config: ICrawlerConfig | None = None) -> str:
        """Fetch ``url`` and return the raw page payload.

        Args:
            url: Company page URL to fetch.
            config: Carries proxy, timeout and browser flags.

        Returns:
            Raw page content (HTML or extracted embedded JSON as text).

        Raises:
            Exception: Any transport failure, or when the response lacks
                the expected embedded payload — chains rely on this to
                fall through to the next scraper.
        """
        pass


class CompanyNameScraper(ABC):
    """Fetches raw search results for a company-name query (I/O only)."""

    @abstractmethod
    def scrape(self, query: str, config: ICrawlerConfig | None = None) -> str:
        """Fetch raw search results for ``query``.

        Args:
            query: Free-text company name.
            config: Carries proxy, timeout and browser flags.

        Returns:
            Raw search response body as text, for a
            :class:`SearchResponseParser` to interpret.

        Raises:
            Exception: Any transport failure; chains rely on this to
                fall through to the next scraper.
        """
        pass
