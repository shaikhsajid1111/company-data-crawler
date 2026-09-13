"""company-data-crawler.

A web crawler package that searches companies and extracts firmographic
data (funding, employees, locations, executives, financials, ...) into a
validated :class:`company_data_crawler.CompanyData` model.

Sources are pluggable: pass a plain string (e.g. ``source="craft"``) to the
crawler, and register new sources (owler, crunchbase, ...) with
``@SourceRegistry.register("name")``.
"""

from typing import List, Optional

from company_data_crawler.interfaces.iconfig import ICrawlerConfig, IQuery
from company_data_crawler.interfaces.search_response import ISearchResponse
from company_data_crawler.models.company_data import CompanyData
from company_data_crawler.sources.base import SourceProvider
from company_data_crawler.sources.registry import SourceRegistry

__version__ = "2.0.0"

__all__ = [
    "CompanyDataCrawler",
    "CompanyData",
    "IQuery",
    "ICrawlerConfig",
    "ISearchResponse",
    "SourceProvider",
    "SourceRegistry",
    "register_source",
]


def register_source(name: str):
    """Decorator alias for registering a new data source by string name.

    Thin wrapper around :meth:`SourceRegistry.register` so source
    authors only need to import from the top-level package::

        from company_data_crawler import SourceProvider, register_source

        @register_source("crunchbase")
        class CrunchbaseSource(SourceProvider):
            ...

    Args:
        name: Source key users will pass as ``source="..."``.
            Case-insensitive; surrounding whitespace is ignored.

    Returns:
        The class decorator that registers the provider.
    """
    return SourceRegistry.register(name)


class CompanyDataCrawler:
    """High-level facade for company search and firmographic data scraping.

    The data source is selected with a plain string, e.g.::

        crawler = CompanyDataCrawler()

        results = crawler.search_company("stripe", source="craft")
        data = crawler.get_company_data(results[0].source_url, source="craft")

    Stock tickers can be resolved to companies with
    :meth:`search_company_by_symbol` / :meth:`get_company_data_by_symbol`.

    New sources (owler, crunchbase, ...) are added by subclassing
    :class:`SourceProvider` and registering them::

        @register_source("owler")
        class OwlerSource(SourceProvider):
            ...

    after which ``source="owler"`` works everywhere.
    """

    def __init__(
        self,
        config: ICrawlerConfig | None = None,
        cache_dir: str | None = None,
    ) -> None:
        """Create the facade with default config and an empty provider cache.

        Args:
            config: Default crawl settings used when a call does not pass
                its own ``config``. A fresh :class:`ICrawlerConfig` is
                built when omitted.
            cache_dir: Base directory for the on-disk caches. Each source
                provider receives it and stores ``CompanyData`` /
                ``ISearchResponse`` records underneath. Falls back to the
                current working directory when omitted.
        """
        self.config = config or ICrawlerConfig()
        self.cache_dir = cache_dir
        self._providers = {}

    def _get_provider(self, source: str) -> SourceProvider:
        """Instantiate (and cache) the provider for the given source string."""
        key = (source or "").strip().lower()
        if key not in self._providers:
            self._providers[key] = SourceRegistry.create(key, cache_dir=self.cache_dir)
        return self._providers[key]

    def available_sources(self) -> list[str]:
        """Names of all registered data sources."""
        return SourceRegistry.available_sources()

    def search_company(
        self,
        query: str,
        source: str = "craft",
        config: ICrawlerConfig | None = None,
    ) -> list[ISearchResponse]:
        """Search companies by name on the given source.

        Args:
            query: Free-text company name, e.g. ``"stripe"``.
            source: Registered source key (``"craft"``, ``"owler"``, ...).
                Case-insensitive.
            config: Per-call crawl settings. Falls back to the facade-level
                config when omitted.

        Returns:
            A list of :class:`ISearchResponse` suggestions (name, canonical
            page URL, slug, logo). Empty when nothing matched.

        Raises:
            ValueError: If ``source`` is not registered.
        """
        return self._get_provider(source).search_company(query, config or self.config)

    def search_company_by_symbol(
        self,
        symbol: str,
        source: str = "craft",
        config: ICrawlerConfig | None = None,
    ) -> list[ISearchResponse]:
        """Search companies by stock ticker on the given source.

        The ticker is resolved to a company name via Yahoo Finance (see
        ``SourceProvider.search_company_by_symbol``) and the resulting name
        is fed through the source's regular name search.

        Args:
            symbol: Exchange ticker, e.g. ``"MSFT"`` (case-insensitive).
            source: Registered source key (``"craft"``, ``"owler"``, ...).
                Case-insensitive.
            config: Per-call crawl settings. Falls back to the facade-level
                config when omitted.

        Returns:
            A list of :class:`ISearchResponse` suggestions for the resolved
            company name. Empty when nothing matched.

        Raises:
            ValueError: If ``source`` is not registered, or the ticker symbol
                is empty or cannot be resolved.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Ticker symbol must not be empty.")
        return self._get_provider(source).search_company_by_symbol(
            symbol, config or self.config
        )

    def get_company_data(
        self,
        url: str,
        source: str = "craft",
        config: ICrawlerConfig | None = None,
    ) -> CompanyData | None:
        """Scrape a company page URL on the given source.

        Args:
            url: Canonical company page URL, usually taken from an
                :class:`ISearchResponse` (``source_url``).
            source: Registered source key the URL belongs to.
            config: Per-call crawl settings. Falls back to the facade-level
                config when omitted.

        Returns:
            The parsed :class:`CompanyData`, served from cache when fresh,
            or ``None`` when the page could not be parsed.

        Raises:
            ValueError: If ``source`` is not registered.
        """
        return self._get_provider(source).get_company_data(url, config or self.config)

    def get_company_data_by_symbol(
        self,
        symbol: str,
        source: str = "craft",
        config: ICrawlerConfig | None = None,
    ) -> CompanyData | None:
        """Resolve a ticker to a company name, then scrape the first search hit.

        Convenience wrapper combining :meth:`search_company_by_symbol` and
        :meth:`get_company_data`. Only the top-ranked search hit is scraped;
        use the two calls separately when you need to choose among hits.

        Args:
            symbol: Exchange ticker, e.g. ``"MSFT"``.
            source: Registered source key.
            config: Per-call crawl settings. Falls back to the facade-level
                config when omitted.

        Returns:
            The parsed :class:`CompanyData` for the first hit, or ``None``
            when the ticker could not be resolved, search returned nothing,
            or the page could not be parsed.

        Raises:
            ValueError: If ``source`` is not registered, or the ticker symbol
                is empty or cannot be resolved.
        """
        results = self.search_company_by_symbol(symbol, source, config)
        if not results:
            return None
        return self.get_company_data(results[0].source_url, source, config)

    def get_company_data_by_name(
        self,
        name: str,
        source: str = "craft",
        config: ICrawlerConfig | None = None,
    ) -> CompanyData | None:
        """Search a company by name, then scrape the first matching page.

        Convenience wrapper combining :meth:`search_company` and
        :meth:`get_company_data`. Only the top-ranked search hit is scraped;
        use the two calls separately when you need to choose among hits.

        Args:
            name: Free-text company name, e.g. ``"airbnb"``.
            source: Registered source key.
            config: Per-call crawl settings. Falls back to the facade-level
                config when omitted.

        Returns:
            The parsed :class:`CompanyData` for the first hit, or ``None``
            when search returned nothing or the page could not be parsed.

        Raises:
            ValueError: If ``source`` is not registered.
        """
        results = self.search_company(name, source, config)
        if not results:
            return None
        return self.get_company_data(results[0].source_url, source, config)
