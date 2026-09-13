"""Search-by-symbol entry point: resolve ticker -> company name -> delegate to name search.

This module is the public API for symbol lookups. It wires a
:class:`YahooFinanceTickerResolver` (which asks Yahoo Finance *“which company
owns ticker MSFT?”*) to a source's existing :class:`CompanySearchByName`
implementation. The resolved name is then fed into the usual name-search path,
so the rest of the pipeline (search -> parse -> scrape -> cache) stays unchanged.
"""

from typing import Optional

from company_data_crawler.base.searcher import CompanySearcher
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.interfaces.search_response import ISearchResponse
from company_data_crawler.searchers.yahoo_finance_ticker_resolver import (
    YahooFinanceTickerResolver,
)

logger = __import__("company_data_crawler.logger", fromlist=["get_logger"]).get_logger(
    __name__
)


class CompanySearchBySymbol(CompanySearcher):
    """Resolve a stock ticker through Yahoo Finance, then search by the resulting name.

    This searcher implements :meth:`search_by_symbol` by delegating to two
    collaborators:

    1. :class:`YahooFinanceTickerResolver` – fetches
       ``https://finance.yahoo.com/quote/<SYMBOL>/`` and extracts the company
       name.
    2. A wrapped :class:`CompanySearcher` (almost always a
       :class:`CompanySearchByName` instance from a specific source) – runs the
       normal name search using the resolved name.

    Because the heavy lifting is done by the wrapped searcher, this class is
    source-agnostic: the same ``CompanySearchBySymbol`` can be paired with
    ``Craft``, ``Owler``, or any future source that implements name search.
    """

    def __init__(
        self,
        name_searcher: CompanySearcher,
        ticker_resolver: YahooFinanceTickerResolver | None = None,
        cache_dir: str | None = None,
    ) -> None:
        """Wire the name searcher and an optional ticker resolver.

        Args:
            name_searcher: Existing ``CompanySearcher`` that implements
                ``search_by_name`` (e.g. the source's ``CompanySearchByName``).
            ticker_resolver: Resolves ticker symbols to company names. A fresh
                ``YahooFinanceTickerResolver`` is created when omitted.
            cache_dir: Base directory for the resolver's
                ``TickerResolution`` disk cache (used only when
                ``ticker_resolver`` is omitted).
        """
        self.name_searcher = name_searcher
        self.ticker_resolver = ticker_resolver or YahooFinanceTickerResolver(
            cache_dir=cache_dir
        )

    def search_by_name(
        self,
        name: str,
        config: ICrawlerConfig | None = None,
    ) -> list[ISearchResponse]:
        """Forward to the wrapped name searcher unchanged."""
        return self.name_searcher.search_by_name(name, config)

    def search_by_symbol(
        self,
        symbol: str,
        config: ICrawlerConfig | None = None,
    ) -> list[ISearchResponse]:
        """Resolve ``symbol`` to a company name, then search by that name.

        Args:
            symbol: Exchange ticker, e.g. ``"MSFT"`` (case-insensitive).
            config: Forwarded to both the resolver and the name searcher.

        Returns:
            Parsed :class:`ISearchResponse` suggestions for the resolved
            company name (may be empty if the company does not appear in the
            source's index).
        """
        company_name = self.ticker_resolver.resolve(symbol, config)
        logger.info(
            "Resolved ticker %r -> %r; delegating to name search", symbol, company_name
        )
        return self.name_searcher.search_by_name(company_name, config)
