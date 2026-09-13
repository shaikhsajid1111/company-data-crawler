"""Craft parsers: page + search-response parsing."""

from company_data_crawler.sources.craft.parsers.company_page_parser import (
    CraftParser,
)
from company_data_crawler.sources.craft.parsers.search_result_parser import (
    CraftSearchParser,
)

__all__ = ["CraftParser", "CraftSearchParser"]
