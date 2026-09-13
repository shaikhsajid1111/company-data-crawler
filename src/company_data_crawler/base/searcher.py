"""Searcher contract: scrape + parse a company search in one step."""

from abc import ABC, abstractmethod
from typing import Optional

from company_data_crawler.base.scraper import CompanyNameScraper
from company_data_crawler.base.search_parser import SearchResponseParser
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.interfaces.search_response import ISearchResponse


class CompanySearcher(ABC):
    """Binds a :class:`CompanyNameScraper` to its response parser.

    Subclasses implement the lookup strategy (by name today, by stock
    symbol when a source supports it).
    """

    def __init__(
        self, searcher: CompanyNameScraper, search_response_parser: SearchResponseParser
    ):
        """Wire the fetch half to the parse half.

        Args:
            searcher: Performs the raw search request.
            search_response_parser: Turns the raw response into
                :class:`ISearchResponse` suggestions.
        """
        self.searcher = searcher
        self.search_response_parser = search_response_parser

    @abstractmethod
    def search_by_name(
        self, name: str, config: ICrawlerConfig | None = None
    ) -> list[ISearchResponse]:
        """Search companies by name.

        Args:
            name: Free-text company name.
            config: Crawl settings forwarded to the scraper.

        Returns:
            Ranked :class:`ISearchResponse` suggestions (maybe empty).
        """
        pass

    @abstractmethod
    def search_by_symbol(
        self, symbol: str, config: ICrawlerConfig | None = None
    ) -> list[ISearchResponse]:
        """Search companies by stock ticker symbol.

        Args:
            symbol: Exchange ticker, e.g. ``"CRWD"``.
            config: Crawl settings forwarded to the scraper.

        Returns:
            Matching suggestions.

        Raises:
            NotImplementedError: Until a source implements symbol search.
        """
        pass
