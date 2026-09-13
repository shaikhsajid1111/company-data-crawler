from typing import Optional

from company_data_crawler.base.searcher import CompanySearcher
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.interfaces.search_response import ISearchResponse


class CompanySearchByName(CompanySearcher):
    """Name search implemented as scrape-then-parse.

    Delegates transport to the injected :class:`CompanyNameScraper`
    and interpretation to the injected
    :class:`SearchResponseParser`; no source-specific logic lives here.
    """

    def search_by_name(
        self, name: str, config: ICrawlerConfig | None = None
    ) -> list[ISearchResponse]:
        """Scrape raw results for ``name`` and parse them to suggestions.

        Args:
            name: Free-text company name.
            config: Forwarded to the underlying scraper.

        Returns:
            Parsed :class:`ISearchResponse` suggestions.
        """
        response = self.searcher.scrape(name, config)
        return self.search_response_parser.parse(response)

    def search_by_symbol(
        self, symbol: str, config: ICrawlerConfig | None = None
    ) -> list[ISearchResponse]:
        """Search by stock ticker (not implemented by any source).

        Args:
            symbol: Exchange ticker.

        Raises:
            NotImplementedError: Always, until symbol search lands.
        """
        raise NotImplementedError("Search by stock symbol is not implemented yet.")
