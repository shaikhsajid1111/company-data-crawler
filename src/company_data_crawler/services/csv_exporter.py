import pandas as pd

from company_data_crawler.models.company_data import CompanyData
from company_data_crawler.services._flattening import RecordFlattener


class CSVExporter:
    """Export CompanyData to CSV (flat, single-row) format.

    Requires the ``export`` extra (pandas). Nested dicts are flattened
    with dotted column names and lists of dicts are expanded into
    indexed columns (e.g. ``key_executives_1.name``).
    """

    def export_data(self, data: CompanyData, filepath: str | None = None):
        """Write ``data`` as a one-row CSV file.

        Args:
            data: Company record (or an already-serialized mapping).
            filepath: Destination path. Defaults to
                ``"company_data.csv"``.

        Returns:
            The filepath written.
        """
        payload = (
            data.model_dump(mode="json") if isinstance(data, CompanyData) else data
        )
        df = pd.DataFrame([RecordFlattener().flatten(payload)])
        output = filepath or "company_data.csv"
        df.to_csv(output, index=False)
        return output
