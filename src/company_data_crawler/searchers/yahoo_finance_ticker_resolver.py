"""Resolve a stock ticker symbol to a company name via Yahoo Finance.

The actual ``CompanyData`` scraping is delegated to the chosen source
(craft, owler, ...); this module only answers the question
*"which company does ticker MSFT belong to?"* by reading a public,
unauthenticated Yahoo Finance quote page.

Resolutions are persisted on disk (``<cache_dir>/TickerResolution/``)
with the same ``search_cache_expiry_time_days`` TTL the search cache
uses, so repeated symbol lookups skip the Yahoo Finance round-trip.
"""

import os
import re
from typing import Optional

from bs4 import BeautifulSoup
from curl_cffi import requests

from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger
from company_data_crawler.models.ticker_resolution import TickerResolution
from company_data_crawler.storage.persistent_disk_cache import DiskCache
from company_data_crawler.utils.general_utils import GeneralUtils
from company_data_crawler.utils.scraping_utils import ScrapingUtils

logger = get_logger(__name__)


class YahooFinanceTickerResolver:
    """Resolve a stock ticker to its company name by scraping Yahoo Finance.

    Fetches ``https://finance.yahoo.com/quote/<TICKER>/`` and extracts the
    company name from the page ``<h1>`` (falling back to the document
    ``<title>`` and then the ``og:title`` meta tag). The resolved name can
    be fed straight into a source's name search.
    """

    QUOTE_URL_TEMPLATE = "https://finance.yahoo.com/quote/{symbol}/"

    def __init__(self, cache_dir: str | None = None) -> None:
        """Create the resolver and open its ``TickerResolution`` disk cache.

        Args:
            cache_dir: Base directory for the on-disk cache. Every resolved
                ticker is stored under ``<cache_dir>/TickerResolution/`` and
                shared by all resolver instances pointing at the same
                directory. Falls back to the current working directory.
        """
        self._cache = DiskCache(TickerResolution, cache_dir or os.getcwd())

    @staticmethod
    def build_proxies(proxy: str | None) -> dict | None:
        """Translate ``"host:port"`` config into the ``curl_cffi`` proxy mapping."""
        if not proxy:
            return None
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    def resolve(self, symbol: str, config: ICrawlerConfig | None = None) -> str:
        """Return the company name for ``symbol``, cached on disk when fresh.

        The ``ticker -> company name`` mapping is persisted under
        ``<cache_dir>/TickerResolution/`` keyed by the uppercase ticker and
        expires after ``search_cache_expiry_time_days``;
        ``config.force_rescrape=True`` bypasses and refreshes the entry.

        Args:
            symbol: Exchange ticker, e.g. ``"MSFT"`` (case-insensitive).
            config: Carries proxy / timeout / cache settings.

        Returns:
            The resolved company name, e.g. ``"Microsoft Corporation"``.

        Raises:
            ValueError: If ``symbol`` is empty, the page could not be
                fetched, or the company name could not be extracted.
        """
        symbol_clean = (symbol or "").strip().upper()
        if not symbol_clean:
            raise ValueError("Ticker symbol must not be empty.")

        crawler_config = config or ICrawlerConfig()

        # 1. Fresh cache entry -> no network round-trip at all.
        if not crawler_config.force_rescrape:
            cached = self._cache.get(symbol_clean)
            if isinstance(cached, TickerResolution) and cached.company_name:
                logger.info(
                    "Ticker %s -> %r (served from TickerResolution cache)",
                    symbol_clean,
                    cached.company_name,
                )
                return cached.company_name

        # 2. Cache miss (or force_rescrape): fetch live, then persist.
        company_name = self._fetch_company_name(symbol_clean, crawler_config)
        if not company_name:
            raise ValueError(
                f"Could not extract a company name from the Yahoo Finance page "
                f"for ticker {symbol_clean!r}. The page may have changed or "
                f"the ticker may be invalid."
            )

        self._cache.set(
            symbol_clean,
            TickerResolution(ticker=symbol_clean, company_name=company_name),
            GeneralUtils.generate_time_from_now(
                crawler_config.search_cache_expiry_time_days
            ).timestamp(),
        )
        logger.info("Resolved ticker %s -> company name %r", symbol_clean, company_name)
        return company_name

    def _fetch_company_name(
        self, symbol: str, config: ICrawlerConfig | None = None
    ) -> str:
        """Fetch the Yahoo Finance quote page and extract the company name.

        Kept separate from :meth:`resolve` so tests (and subclasses) can
        stub the network step while the caching behaviour stays intact.

        Args:
            symbol: Uppercase ticker, e.g. ``"MSFT"``.
            config: Carries proxy / timeout settings; defaults when omitted.

        Returns:
            The extracted company name, or ``""`` when extraction failed.
        """
        url = self.QUOTE_URL_TEMPLATE.format(symbol=symbol)
        logger.info("Resolving ticker %s via %s", symbol, url)

        proxy = config.proxy if config else None
        response = requests.get(
            url,
            headers=ScrapingUtils.prepare_default_headers(),
            impersonate="chrome",
            proxies=self.build_proxies(proxy),
            timeout=config.request_timeout if config else 30.0,
        )
        response.raise_for_status()

        return self._extract_company_name(response.text, symbol)

    @classmethod
    def _extract_company_name(cls, html: str, symbol: str) -> str:
        """Best-effort extraction of the company name from a Yahoo Finance page.

        Tries, in order:
        1.  the ``<h1>`` heading   — e.g. ``"Microsoft Corporation (MSFT)"``
        2.  the ``<title>`` tag    — e.g. ``"Microsoft Corporation (MSFT) Stock Price..."``
        3.  the ``og:title`` meta  — same shape as ``<title>``
        """
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("title")
        if title_tag:
            name = cls._clean_company_name(title_tag.get_text(" ", strip=True), symbol)
            if name:
                return name

        meta = soup.find("meta", attrs={"property": "og:title"})
        if meta and meta.get("content"):
            name = cls._clean_company_name(meta["content"], symbol)
            if name:
                return name

        return ""

    @staticmethod
    def _clean_company_name(text: str, symbol: str) -> str:
        """Strip the ticker suffix and Yahoo boilerplate from a heading/title.

        Handles:
        - ``"Microsoft Corporation (MSFT)"``            -> ``"Microsoft Corporation"``
        - ``"Microsoft Corporation (MSFT) Stock Price..."`` -> ``"Microsoft Corporation"``
        """
        if not text:
            return ""

        # Cut at Yahoo boilerplate markers (title tags append them).
        name = re.split(
            r"\s+\|\s*.*$|\s+Stock Price.*$|\s+Quote.*$|\s+News, & Info.*$",
            text.strip(),
            maxsplit=1,
        )[0]
        name = name.strip().strip("|").strip()

        # Remove a trailing " (TICKER)" suffix, e.g. "Microsoft Corporation (MSFT)".
        if symbol:
            name = re.sub(rf"\(\s*{re.escape(symbol)}\s*\)\s*$", "", name).strip()

        return name
