from typing import Optional

from company_data_crawler.base.searcher import CompanySearcher
from company_data_crawler.interfaces.iconfig import ICrawlerConfig, IQuery
from company_data_crawler.interfaces.search_response import ISearchResponse
from company_data_crawler.models.company_data import CompanyData
from company_data_crawler.orchestrators.scraping_orchestrator import (
    CompanyPageScrapingService,
)
from company_data_crawler.orchestrators.search_orchestrator import (
    CompanySearchingService,
)
from company_data_crawler.searchers.search_by_name import CompanySearchByName
from company_data_crawler.sources.base import SourceProvider
from company_data_crawler.sources.owler.crawlers.company_name_scraper_chain import (
    OwlerCompanyNameScraperChain,
)
from company_data_crawler.sources.owler.crawlers.http_company_search_crawler import (
    OwlerCompanySearchService,
)
from company_data_crawler.sources.owler.crawlers.http_url_crawler import (
    OwlerHttpUrlScraper,
)
from company_data_crawler.sources.owler.crawlers.selenium_base_search_crawler import (
    OwlerSeleniumSearchCrawler,
)
from company_data_crawler.sources.owler.crawlers.selenium_base_url_crawler import (
    OwlerSeleniumUrlScraper,
)
from company_data_crawler.sources.owler.crawlers.url_scraper_chain import (
    OwlerUrlScraperChain,
)
from company_data_crawler.sources.owler.parser.company_page_parser import (
    OwlerParser,
)
from company_data_crawler.sources.owler.parser.search_result_parser import (
    OwlerSearchParser,
)
from company_data_crawler.sources.registry import SourceRegistry


@SourceRegistry.register("owler")
class OwlerSource(SourceProvider):
    """owler.com provider: company search + firmographic page scraping."""

    source_name = "owler"

    def __init__(
        self,
        cache_dir: str | None = None,
        searcher=None,
        url_scraper=None,
        page_parser=None,
    ) -> None:
        """Build search + scraping services with HTTP → Selenium fallbacks.

        Defaults wire Owler's search chain (HTTP crawler, then Selenium)
        with its search-response parser, and the page chain (HTTP
        scraper, then Selenium) with its page parser. The ``searcher`` /
        ``url_scraper`` / ``page_parser`` overrides are
        dependency-injection seams for tests and power users: a raw
        scraper is auto-wrapped with this source's response parser.

        Args:
            cache_dir: Base dir for this source's disk caches.
            searcher: Custom :class:`CompanySearcher` (or bare
                :class:`CompanyNameScraper`) replacing the default chain.
            url_scraper: Custom :class:`UrlScraper` replacing the
                default page chain.
            page_parser: Custom :class:`Parser` replacing the default.
        """
        self.cache_dir = cache_dir
        if searcher is not None and not isinstance(searcher, CompanySearcher):
            # Accept a raw CompanyNameScraper too, and wrap it with Owler's
            # search-response parser for convenience.
            searcher = CompanySearchByName(searcher, OwlerSearchParser())
        self.search_service = CompanySearchingService(
            searcher=searcher
            or CompanySearchByName(
                OwlerCompanyNameScraperChain(
                    (OwlerCompanySearchService(), OwlerSeleniumSearchCrawler())
                ),
                OwlerSearchParser(),
            ),
            source_name=self.source_name,
            cache_dir=cache_dir,
        )
        self.scraping_service = CompanyPageScrapingService(
            page_parser=page_parser or OwlerParser(),
            url_scraper=url_scraper
            or OwlerUrlScraperChain((OwlerHttpUrlScraper(), OwlerSeleniumUrlScraper())),
            cache_dir=cache_dir,
        )

    def search_company(
        self,
        query: str,
        config: ICrawlerConfig | None = None,
    ) -> list[ISearchResponse]:
        """Search companies by name on owler.com (cached).

        Args:
            query: Free-text company name; wrapped into
                ``IQuery(company_name=...)``.
            config: Per-call crawl settings.

        Returns:
            Suggestion list (possibly empty).
        """
        return self.search_service.search_company(IQuery(company_name=query), config)

    def get_company_data(
        self,
        url: str,
        config: ICrawlerConfig | None = None,
    ) -> CompanyData | None:
        """Scrape an owler.com company page URL into CompanyData (cached).

        Args:
            url: Canonical company page URL.
            config: Per-call crawl settings.

        Returns:
            The parsed record, or ``None`` when unparseable.
        """
        return self.scraping_service.scrape_company_page(url, config)
