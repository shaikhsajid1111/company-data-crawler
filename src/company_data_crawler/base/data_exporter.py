"""Exporter contract: persist a CompanyData record to a file format."""

from abc import ABC, abstractmethod

from company_data_crawler.models.company_data import CompanyData


class DataExporter(ABC):
    """Abstract exporter turning :class:`CompanyData` into a file.

    Concrete exporters (JSON, CSV, Excel, Parquet) differ only in
    serialization; all of them accept either a validated
    :class:`CompanyData` or an already-serialized mapping.
    """

    @abstractmethod
    def export_data(self, data: CompanyData, filepath: str | None = None):
        """Write ``data`` to ``filepath``.

        Args:
            data: The company record to export.
            filepath: Destination path. Each exporter defines a sensible
                default (e.g. ``"company_data.json"``) when omitted.

        Returns:
            The filepath written, or — for exporters that support it —
            the serialized payload itself when no filepath is given.
        """
        pass
