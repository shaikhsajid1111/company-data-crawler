from collections.abc import Iterable

from company_data_crawler.base.scraper import CompanyNameScraper
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger

logger = get_logger("Company name scraper chain")


class CompanyNameScraperChain(CompanyNameScraper):
    """Try company-name scrapers in order until one returns a response."""

    def __init__(self, scrapers: Iterable[CompanyNameScraper]):
        """Chain name-search scrapers tried in order until one responds.

        Args:
            scrapers: Non-empty sequence of :class:`CompanyNameScraper`.

        Raises:
            ValueError: If ``scrapers`` is empty.
        """
        self.scrapers = tuple(scrapers)
        if not self.scrapers:
            raise ValueError("CompanyNameScraperChain requires at least one scraper")

    def scrape(self, query: str, config: ICrawlerConfig | None = None) -> str:
        """Return the first successful raw search response for ``query``.

        Failures are logged and iteration continues; the last error is
        re-raised when every scraper fails.

        Args:
            query: Free-text company name.
            config: Forwarded to every chained scraper.

        Returns:
            Raw search response body.

        Raises:
            Exception: The last scraper's error, if none succeeded.
        """
        last_error: Exception | None = None

        for scraper in self.scrapers:
            try:
                logger.info("Trying %s for %s", type(scraper).__name__, query)
                return scraper.scrape(query, config)
            except Exception as ex:
                last_error = ex
                logger.warning(
                    "%s failed for %s; trying the next scraper",
                    type(scraper).__name__,
                    query,
                    exc_info=True,
                )

        assert last_error is not None
        raise last_error
