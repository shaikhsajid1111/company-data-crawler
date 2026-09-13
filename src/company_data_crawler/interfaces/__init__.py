"""Convenience re-exports of the config/query/response models."""

from company_data_crawler.interfaces.iconfig import (
    ICrawlerConfig,
    IQuery,
    IDatabaseConfig,
)
from company_data_crawler.interfaces.search_response import ISearchResponse

__all__ = [
    "ICrawlerConfig",
    "IQuery",
    "IDatabaseConfig",
    "ISearchResponse",
]
