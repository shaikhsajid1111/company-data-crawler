import re
from dataclasses import dataclass
from typing import Any, Optional

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb

from company_data_crawler.base.storage import DataStorage
from company_data_crawler.interfaces.iconfig import IDatabaseConfig
from company_data_crawler.models.company_data import CompanyData

DEFAULT_COMPANY_DATA_TABLE = "company_data"

# libpq connection keywords accepted from IDatabaseConfig.extra_options. Any
# extra option outside this set (e.g. Mongo-specific ones such as
# "retryWrites") is ignored instead of breaking the psycopg connection.
_VALID_CONNINFO_PARAMS = frozenset(
    {
        "application_name",
        "client_encoding",
        "connect_timeout",
        "dbname",
        "fallback_application_name",
        "gssencmode",
        "host",
        "hostaddr",
        "keepalives",
        "keepalives_count",
        "keepalives_idle",
        "keepalives_interval",
        "krbsrvname",
        "load_balance_hosts",
        "options",
        "passfile",
        "password",
        "port",
        "replication",
        "require_auth",
        "requirepeer",
        "service",
        "ssl_min_protocol_version",
        "ssl_max_protocol_version",
        "sslcrl",
        "sslcrldir",
        "sslsni",
        "sslcert",
        "sslcompression",
        "sslkey",
        "sslmode",
        "sslpassword",
        "sslrootcert",
        "target_session_attrs",
        "user",
    }
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DSN_SCHEME_RE = re.compile(r"^postgres(?:ql)?(?:\+[A-Za-z0-9_]+)?://")


@dataclass(frozen=True)
class PostgresUpdateResult:
    """Outcome of an upsert, mirroring the attributes of pymongo's UpdateResult."""

    matched_count: int
    upserted_id: str | None
    rowcount: int
    acknowledged: bool = True


class PostgreSQLStorage(DataStorage):
    """Stores CompanyData documents in PostgreSQL.

    The whole CompanyData payload is persisted as a JSONB document keyed by
    the company domain, so a single row per company is kept up to date with
    the same upsert semantics as Mongo's update_one(..., upsert=True). Nested
    structures (funding info, executives, locations, ...) stay queryable
    through JSONB operators, and new fields added to CompanyData keep working
    without a migration.
    """

    def __init__(self, config: IDatabaseConfig) -> None:
        """Store the DB config; no connection is opened yet.

        Args:
            config: Supplies the DSN plus ``extra_options`` — a custom
                table name via ``table`` and libpq keywords (only
                allow-listed ones in ``_VALID_CONNINFO_PARAMS`` reach
                psycopg).
        """
        self.config = config

    def connect(self) -> None:
        self.pg_connection: Connection = psycopg.connect(
            self._dsn(), autocommit=True, **self._connection_options()
        )
        self.company_data_table: str = self.config.extra_options.get(
            "table", DEFAULT_COMPANY_DATA_TABLE
        )
        self._ensure_company_data_table()

    def store_data(self, company_data: CompanyData) -> PostgresUpdateResult:
        with self.pg_connection.cursor() as cursor:
            cursor.execute(
                self._upsert_sql(),
                (
                    company_data.company_domain,
                    Jsonb(company_data.model_dump(mode="json")),
                ),
            )
            row = cursor.fetchone()
            rowcount = cursor.rowcount
        # "RETURNING (xmax = 0)" tells a fresh INSERT (True) apart from the
        # UPDATE of an already existing row (False).
        inserted = bool(row and row[0])
        if inserted:
            return PostgresUpdateResult(
                matched_count=0,
                upserted_id=company_data.company_domain,
                rowcount=rowcount,
            )
        return PostgresUpdateResult(
            matched_count=1, upserted_id=None, rowcount=rowcount
        )

    def close(self) -> None:
        """Close the PostgreSQL connection."""
        self.pg_connection.close()

    def _dsn(self) -> str:
        """Config DSN normalized to the postgresql:// scheme libpq expects."""
        return _DSN_SCHEME_RE.sub("postgresql://", self.config.dsn)

    def _connection_options(self) -> dict[str, Any]:
        """Filter ``extra_options`` down to valid libpq keywords.

        Mongo-specific keys (e.g. ``retryWrites``) are dropped so a
        shared config object cannot break ``psycopg.connect``.
        """
        return {
            key: value
            for key, value in self.config.extra_options.items()
            if key in _VALID_CONNINFO_PARAMS
        }

    def _ensure_company_data_table(self) -> None:
        """Create ``(company_domain TEXT PRIMARY KEY, data JSONB)`` if missing.

        Raises:
            ValueError: If the configured table name is not a safe SQL
                identifier.
        """
        table = self.company_data_table
        if not _IDENTIFIER_RE.match(table):
            raise ValueError(f"Invalid table name: {table!r}")
        self.pg_connection.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                company_domain TEXT PRIMARY KEY,
                data JSONB NOT NULL
            )
            """)

    def _upsert_sql(self) -> str:
        """Return the ``INSERT ... ON CONFLICT DO UPDATE ... RETURNING (xmax = 0)`` statement used to distinguish fresh inserts from updates of an existing domain row."""
        return f"""
            INSERT INTO {self.company_data_table} (company_domain, data)
            VALUES (%s, %s)
            ON CONFLICT (company_domain)
            DO UPDATE SET data = EXCLUDED.data
            RETURNING (xmax = 0) AS inserted
        """
