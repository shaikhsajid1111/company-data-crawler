"""Ticker-resolution cache record: which company owns a stock ticker."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TickerResolution(BaseModel):
    """A resolved ``ticker -> company name`` mapping, persisted on disk.

    Produced by
    :class:`company_data_crawler.searchers.yahoo_finance_ticker_resolver.YahooFinanceTickerResolver`
    so repeated symbol searches (``MSFT`` -> ``Microsoft Corporation``)
    skip the Yahoo Finance round-trip while the entry is fresh. Entries
    live under ``<cache_dir>/TickerResolution/`` and expire with the
    ``search_cache_expiry_time_days`` TTL.
    """

    ticker: str = Field(..., description="Uppercase stock ticker symbol, e.g. MSFT")
    company_name: str = Field(
        ..., description="The company name the ticker resolved to"
    )
    last_resolved_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="The timestamp when the ticker was last resolved",
    )
