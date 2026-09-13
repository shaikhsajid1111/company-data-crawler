"""Storage contract: persist a CompanyData record to a database."""

from abc import ABC, abstractmethod

from company_data_crawler.models.company_data import CompanyData


class DataStorage(ABC):
    """Database sink for :class:`CompanyData` documents.

    Implementations upsert whole records keyed by ``company_domain``,
    so re-scraping a company refreshes its row/document in place.
    """

    @abstractmethod
    def connect(self):
        """Open the connection and prepare the destination (create the table/collection if missing). Must be called before :meth:`store_data`."""
        pass

    @abstractmethod
    def store_data(self, company_data: CompanyData):
        """Upsert one company record keyed by ``company_domain``.

        Args:
            company_data: Validated record to persist.

        Returns:
            The driver-specific upsert outcome (e.g. pymongo's
            ``UpdateResult`` or :class:`PostgresUpdateResult`).
        """
        pass
