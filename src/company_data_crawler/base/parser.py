"""Page-parser contract: raw page payload -> CompanyData."""

from abc import ABC, abstractmethod
from typing import Optional

from company_data_crawler.models.company_data import CompanyData


class Parser(ABC):
    """Maps a source-specific raw page onto :class:`CompanyData`.

    Implementations are pure functions of the fetched payload: they
    perform no I/O and must tolerate missing fields by falling back to
    the model defaults.
    """

    @abstractmethod
    def parse(self, data: str) -> CompanyData | None:
        """Parse a raw page payload into :class:`CompanyData`.

        Args:
            data: Raw page content as returned by the matching
                :class:`UrlScraper` (typically a JSON string extracted
                from the page's embedded state).

        Returns:
            The validated company record, or ``None`` when the payload
            carries no recognizable company data.
        """
        pass
