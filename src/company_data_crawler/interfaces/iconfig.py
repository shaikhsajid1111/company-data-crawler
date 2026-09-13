from pydantic import BaseModel, Field, model_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Any


class ICrawlerConfig(BaseModel):
    """Per-call or facade-level crawl settings.

    Passed down to every scraper in the chain (HTTP timeouts/proxies
    and Selenium UC/headless flags) and to the orchestrators for cache
    TTLs. Values are validated: ``request_timeout`` must be positive.
    """

    request_timeout: float = Field(default=30.0, gt=0)
    user_agent: str = ""
    proxy: str | None = None
    headless: bool = True
    uc: bool = True
    company_cache_expiry_time_days: int = Field(default=90)
    search_cache_expiry_time_days: int = Field(default=90)
    force_rescrape: bool = Field(
        default=False,
        description="When set to true, will always bypass cache and scrape the data. Recommended to keep it False",
    )


class IQuery(BaseModel):
    """A company search request: name and/or stock ticker.

    At least one field must be non-empty (enforced by
    :meth:`check_at_least_one`). Only ``company_name`` is honored by
    current sources; ``stock_ticket`` is accepted for forward
    compatibility with symbol search.
    """

    company_name: str = Field(default="")
    stock_ticket: str = Field(default="")

    @model_validator(mode="after")
    def check_at_least_one(self):
        """Reject queries where every field is empty.

        Returns:
            The validated model unchanged.

        Raises:
            ValueError: If both ``company_name`` and ``stock_ticket``
                are empty/missing.
        """
        values = [self.company_name, self.stock_ticket]
        if not any(v is not None and v != "" for v in values):
            raise ValueError("At least one field must be provided and non-empty.")
        return self


class IDatabaseConfig(BaseSettings):
    """Database credentials, readable from ``DB_*`` environment variables.

    ``driver``/``name``/``host``/``port``/``user``/``password`` map to
    the connection; any extra keys (e.g. ``table="company_data"`` for
    Postgres, ``retryWrites`` for Mongo) are kept in
    :attr:`extra_options` for the storage backend to consume.
    """

    model_config = SettingsConfigDict(
        env_prefix="DB_", extra="allow", env_nested_delimiter="__"
    )

    # Core required fields (Now safer and optional for local/SQLite/Mongo)
    driver: str = Field(
        description="Database driver/protocol (e.g., postgresql, mongodb, mysql)"
    )
    name: str = Field(description="Database or scheme name")
    host: str = "localhost"
    port: int | None = None  # None allows us to fallback cleanly based on the driver
    user: str | None = None
    password: str | None = None

    @computed_field
    @property
    def dsn(self) -> str:
        """Assemble a connection string for SQL and NoSQL drivers.

        Handles ``user[:password]@`` auth, Atlas ``mongodb+srv`` URLs
        (no explicit port), and per-driver default ports
        (5432/3306/27017). Falls back to a host-only form for
        path-style systems such as SQLite.
        """
        # 1. Handle credentials safely
        auth = ""
        if self.user and self.password:
            auth = f"{self.user}:{self.password}@"
        elif self.user:
            auth = f"{self.user}@"

        # 2. Handle MongoDB Cloud / Atlas exception (+srv handles ports internally)
        if "+srv" in self.driver or self.driver == "mongodb+srv":
            return f"{self.driver}://{auth}{self.host}/{self.name}"

        # 3. Determine the correct network port if not explicitly provided
        resolved_port = self.port
        if resolved_port is None:
            if "postgres" in self.driver:
                resolved_port = 5432
            elif "mysql" in self.driver:
                resolved_port = 3306
            elif "mongo" in self.driver:
                resolved_port = 27017

        # 4. Return standard connection string format
        if resolved_port:
            return f"{self.driver}://{auth}{self.host}:{resolved_port}/{self.name}"

        # Fallback for systems like SQLite which may just use host/paths
        return f"{self.driver}://{auth}{self.host}/{self.name}"

    @property
    def extra_options(self) -> dict[str, Any]:
        """Safely extract all loose, unmapped configuration settings.

        Returns:
            Every extra key passed to the config (e.g. a Postgres
            ``table`` name or Mongo driver options) as a plain dict.
        """
        all_extras = self.__pydantic_extra__ or {}
        return all_extras
