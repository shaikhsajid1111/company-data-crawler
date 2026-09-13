"""Shared record flattening for tabular exporters (CSV, Excel, Parquet).

``pandas.json_normalize`` only flattens nested *dicts*; lists of dicts are
left as stringified JSON blobs inside a single cell.
:class:`RecordFlattener` additionally expands list elements into indexed
columns, e.g.::

    {"company_funding_info": [{"funding_amount": 100}]}
    -> {"company_funding_info_1.funding_amount": 100}
"""

from typing import Any


class RecordFlattener:
    """Flatten nested dicts and lists of dicts into tabular columns.

    Used by the CSV, Excel and Parquet exporters to turn a single
    (possibly deeply nested) company record into one flat row.

    Args:
        dict_sep: Separator between nested dict keys (default ``"."``).
        list_index_sep: Separator before list element indices
            (default ``"_"``), producing names like ``funding_1.date``.
        index_start: First index used for list elements (default ``1``).
    """

    def __init__(
        self,
        dict_sep: str = ".",
        list_index_sep: str = "_",
        index_start: int = 1,
    ) -> None:
        self.dict_sep = dict_sep
        self.list_index_sep = list_index_sep
        self.index_start = index_start

    def flatten(
        self,
        payload: dict[str, Any] | list[Any],
        prefix: str = "",
    ) -> dict[str, Any]:
        """Flatten ``payload`` into a flat column mapping.

        Args:
            payload: Mapping (or list of mappings) to flatten.
            prefix: Column-name prefix used during recursion.

        Returns:
            A flat mapping suitable for a single tabular row.
        """
        flat: dict[str, Any] = {}
        if isinstance(payload, list):
            self._flatten_list(payload, prefix, flat)
            return flat
        self._flatten_dict(payload, prefix, flat)
        return flat

    @staticmethod
    def _is_list_of_dicts(value: Any) -> bool:
        return (
            isinstance(value, list)
            and len(value) > 0
            and all(isinstance(item, dict) for item in value)
        )

    def _join(self, prefix: str, key: str) -> str:
        return f"{prefix}{self.dict_sep}{key}" if prefix else key

    def _flatten_list(
        self,
        payload: list[Any],
        prefix: str,
        flat: dict[str, Any],
    ) -> None:
        if not prefix:
            return
        if not self._is_list_of_dicts(payload):
            # Lists of scalars are kept intact for the caller to serialize.
            flat[prefix] = payload if payload else None
            return
        for offset, item in enumerate(payload):
            index = self.index_start + offset
            child_prefix = f"{prefix}{self.list_index_sep}{index}"
            flat.update(self.flatten(item, child_prefix))

    def _flatten_dict(
        self,
        payload: dict[str, Any],
        prefix: str,
        flat: dict[str, Any],
    ) -> None:
        for key, value in payload.items():
            column = self._join(prefix, key)
            if isinstance(value, dict) or self._is_list_of_dicts(value):
                self._flatten_container(value, column, flat)
            else:
                flat[column] = value

    def _flatten_container(
        self,
        payload: dict[str, Any] | list[Any],
        column: str,
        flat: dict[str, Any],
    ) -> None:
        if payload:
            flat.update(self.flatten(payload, column))
            return
        flat[column] = None


def flatten_record(
    payload: dict[str, Any] | list[Any],
    prefix: str = "",
) -> dict[str, Any]:
    """Convenience wrapper around :class:`RecordFlattener` defaults."""
    return RecordFlattener().flatten(payload, prefix)
