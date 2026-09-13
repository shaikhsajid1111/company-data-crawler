from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import UpdateResult

from company_data_crawler.base.storage import DataStorage
from company_data_crawler.interfaces.iconfig import IDatabaseConfig
from company_data_crawler.models.company_data import CompanyData


class MongoDBStorage(DataStorage):
    """MongoDB sink: one upserted document per ``company_domain`` in the ``company_data`` collection."""

    def __init__(self, config: IDatabaseConfig) -> None:
        """Store the DB config; no connection is opened yet.

        Args:
            config: Supplies the DSN (``config.dsn``), database name and
                driver ``extra_options`` passed to ``MongoClient``.
        """
        self.config = config

    def connect(self) -> None:
        """Connect via ``MongoClient`` and bind ``db["company_data"]``. Must precede :meth:`store_data`."""
        self.mongo_connection = MongoClient(
            self.config.dsn, **self.config.extra_options
        )
        self.db: Database = self.mongo_connection[self.config.name]
        self.company_data_collection: Collection = self.db["company_data"]

    def store_data(self, company_data: CompanyData) -> UpdateResult:
        """Upsert the record keyed by ``company_domain``.

        Serializes with ``model_dump(mode="json")`` so enums become
        values and datetimes become ISO strings (BSON-safe).

        Args:
            company_data: Validated record to persist.

        Returns:
            pymongo's ``UpdateResult`` for the upsert.
        """
        filter_q = {"company_domain": company_data.company_domain}
        # mode="json" keeps the payload BSON-encodable: nested enums (e.g.
        # CompanyStatus) become their values and datetimes become ISO strings.
        set_q = {"$set": company_data.model_dump(mode="json")}
        result = self.company_data_collection.update_one(
            filter=filter_q, update=set_q, upsert=True
        )
        return result
