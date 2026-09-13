from abc import ABC, abstractmethod
from typing import Optional

from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.interfaces.search_response import ISearchResponse
from company_data_crawler.models.company_data import CompanyData
from company_data_crawler.searchers.yahoo_finance_ticker_resolver import (
    YahooFinanceTickerResolver,
)


class SourceProvider(ABC):
    """Contract every data source must fulfil.

    The crawler is source-agnostic: a *source* (craft, owler, crunchbase, ...)
    is a self-contained bundle of a searcher (find companies by name) and a
    scraper/parser (extract firmographic data from a company page). Users
    select the source with a plain string::

        CompanyDataCrawler().get_company_data(url, source="owler")

    How to implement a new source (e.g. Owler or Crunchbase):

    1. Implement the low-level pieces for that website, subclassing the
       existing base contracts:
       - URL scraping:  ``base.scraper.UrlScraper`` (fetch + return raw page)
       - page parsing:  ``base.parser.Parser`` (raw page -> CompanyData)
       - name search:   ``base.scraper.CompanyNameScraper`` +
                        ``base.search_parser.SearchResponseParser``
                        (query -> List[ISearchResponse])

    2. Subclass ``SourceProvider``, wire the pieces together and register it::

        @SourceRegistry.register("owler")
        class OwlerSource(SourceProvider):
            source_name = "owler"

            def search_company(self, query, config=None):
                return self.search_service.search_company(...)

            def get_company_data(self, url, config=None):
                return self.scraping_service.scrape_company_page(url, config)

    3. Done - the string "owler" is now accepted everywhere.
    """

    source_name: str = ""
    cache_dir: str | None = None

    @abstractmethod
    def search_company(
        self,
        query: str,
        config: ICrawlerConfig | None = None,
    ) -> list[ISearchResponse]:
        """Search companies by name and return search suggestions."""
        ...

    def search_company_by_symbol(
        self,
        symbol: str,
        config: ICrawlerConfig | None = None,
    ) -> list[ISearchResponse]:
        """Resolve a ticker to a company name and run the standard name search.

        The ticker resolution itself is cached on disk under the
        provider's ``cache_dir`` (``TickerResolution/`` namespace), so
        repeated symbol lookups skip the Yahoo Finance round-trip.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Ticker symbol must not be empty.")
        company_name = YahooFinanceTickerResolver(cache_dir=self.cache_dir).resolve(
            symbol.strip(), config
        )
        if not company_name:
            return []
        return self.search_company(company_name, config)

    @abstractmethod
    def get_company_data(
        self,
        url: str,
        config: ICrawlerConfig | None = None,
    ) -> CompanyData | None:
        """Scrape a company page URL and return the parsed CompanyData."""
        ...
