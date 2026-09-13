import pandas as pd

from company_data_crawler.models.company_data import CompanyData
from company_data_crawler.services._flattening import RecordFlattener


class ParquetExporter:
    """Export CompanyData to Parquet (Snappy-compressed, PyArrow engine).

    Requires the ``export`` extra (pandas + PyArrow). The record is
    flattened with the same logic as :class:`CSVExporter`.
    """

    def export_data(self, data: CompanyData, filepath: str | None = None):
        """Write ``data`` as a Parquet dataset.

        Args:
            data: Company record (or an already-serialized mapping).
            filepath: Destination path. Defaults to
                ``"company_data.parquet"``.

        Returns:
            The filepath written.
        """
        payload = (
            data.model_dump(mode="json") if isinstance(data, CompanyData) else data
        )
        df = pd.DataFrame([RecordFlattener().flatten(payload)])
        output = filepath or "company_data.parquet"
        df.to_parquet(path=output, engine="pyarrow", compression="snappy")
        return output
