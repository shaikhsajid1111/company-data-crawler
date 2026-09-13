import pandas as pd

from company_data_crawler.models.company_data import CompanyData
from company_data_crawler.services._flattening import RecordFlattener


class ExcelExporter:
    """Export CompanyData to Excel (.xlsx) format.

    Requires the ``export`` extra (pandas + openpyxl). The record is
    flattened with the same logic as :class:`CSVExporter`.
    """

    def export_data(self, data: CompanyData, filepath: str | None = None):
        """Write ``data`` as a single-sheet ``.xlsx`` workbook.

        Args:
            data: Company record (or an already-serialized mapping).
            filepath: Destination path. Defaults to
                ``"company_data.xlsx"``.

        Returns:
            The filepath written.
        """
        payload = (
            data.model_dump(mode="json") if isinstance(data, CompanyData) else data
        )
        df = pd.DataFrame([RecordFlattener().flatten(payload)])
        output = filepath or "company_data.xlsx"
        df.to_excel(output, index=False, engine="openpyxl")
        return output
