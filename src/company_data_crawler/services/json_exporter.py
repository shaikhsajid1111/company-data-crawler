import json
from typing import Optional

from company_data_crawler.models.company_data import CompanyData


class JSONExporter:
    """Export CompanyData to JSON. Works out of the box (stdlib only)."""

    def export_data(self, data: CompanyData, filepath: str | None = None):
        """Serialize ``data`` to pretty-printed JSON.

        Args:
            data: Company record (or an already-serialized mapping).
            filepath: Destination path. When omitted, nothing is written
                and the JSON string is returned instead.

        Returns:
            The filepath written, or the JSON string when ``filepath``
            is not given.
        """
        payload = (
            data.model_dump(mode="json") if isinstance(data, CompanyData) else data
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(payload, fp=file, indent=2)
            return filepath
        return json.dumps(payload)
