"""Source plumbing: registry + every bundled source (craft, owler) and the provider base contract."""

from company_data_crawler.sources.base import SourceProvider
from company_data_crawler.sources.craft.provider import CraftSource
from company_data_crawler.sources.owler.provider import OwlerSource
from company_data_crawler.sources.registry import SourceRegistry

__all__ = ["SourceProvider", "SourceRegistry", "CraftSource", "OwlerSource"]
