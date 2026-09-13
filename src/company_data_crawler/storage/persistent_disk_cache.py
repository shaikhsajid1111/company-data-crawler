from typing import Optional, TypeVar

import diskcache
from pydantic import BaseModel

from company_data_crawler.base.persistent_cache import PersistentCache

T = TypeVar("T", bound=BaseModel)


class DiskCache(PersistentCache[T]):
    """diskcache-backed implementation of :class:`PersistentCache`.

    Single models serialize via ``model_dump(mode="json")`` (lists stay
    lists), so entries are plain JSON round-trippable back through
    ``model_validate``. Empty/``None`` payloads are silently skipped on
    :meth:`set`; wrong model types raise :class:`TypeError`.
    """

    def __init__(self, model_class: type[T], base_dir: str) -> None:
        """Open (creating if needed) the ``<base_dir>/<ModelName>`` cache folder.

        Args:
            model_class: Model type stored in this namespace.
            base_dir: Parent directory for the model folder.
        """
        super().__init__(model_class, base_dir)
        self._cache = diskcache.Cache(self.folder_path)

    def set(
        self,
        key: str,
        data: T | list[T],
        expiry_time: float,
    ) -> None:
        """Validate, serialize and persist ``data`` under ``key``.

        Args:
            key: Page URL (company cache) or raw query (search cache).
            data: Model instance or list thereof; ``None``/``[]`` are
                ignored.
            expiry_time: Absolute POSIX timestamp forwarded to diskcache
                as the entry's expiry.

        Raises:
            TypeError: If any item is not an instance of the bound model.
        """
        # 1. Early exit if data is empty, None, or an empty list safely
        if data is None or (isinstance(data, list) and not data):
            return

        # 2. Track whether the input data is a list
        is_list = isinstance(data, list)
        items_to_validate = data if is_list else [data]

        # 3. Fast, single-pass type validation for all items
        for item in items_to_validate:
            if not isinstance(item, self._model_class):
                raise TypeError(
                    f"Expected {self._model_class.__name__}, got {type(item).__name__}"
                )

        # 4. Serialize while perfectly preserving the shape (Single dict vs List of dicts)
        if is_list:
            serialized_data = [item.model_dump(mode="json") for item in data]
        else:
            serialized_data = data.model_dump(mode="json")

        # 5. Persist the clean serialized structure
        self._cache.set(key, serialized_data, expire=expiry_time)

    def get(self, key: str) -> T | list[T] | None:
        """Fetch and re-validate the entry for ``key``.

        Args:
            key: The lookup key used at :meth:`set` time.

        Returns:
            A model instance, a list of them (when a list was stored),
            or ``None`` on miss/expiry.
        """
        raw_data = self._cache.get(key)
        if raw_data is None:
            return None

        # If disk has a list, it maps back to a flat list of Pydantic models
        if isinstance(raw_data, list):
            return [self._model_class.model_validate(item) for item in raw_data]

        # If disk has a single dict, it maps back to one Pydantic model
        return self._model_class.model_validate(raw_data)

    def delete(self, key: str) -> None:
        """Remove a single key from this specific cache folder."""
        self._cache.delete(key)

    def clear(self) -> None:
        """Wipe ONLY this specific model's data without affecting other files."""
        self._cache.clear()
