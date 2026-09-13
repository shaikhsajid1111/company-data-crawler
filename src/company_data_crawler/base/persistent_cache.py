"""Persistent-cache contract: typed, per-model on-disk caching."""

import os
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PersistentCache(ABC, Generic[T]):
    """Typed cache namespace for one Pydantic model.

    Each model gets its own folder (``<base_dir>/<ModelName>``), so
    company pages (``CompanyData``) and search hits
    (``ISearchResponse``) never share entries and can be expired or
    wiped independently.
    """

    def __init__(self, model_class: type[T], base_dir: str) -> None:
        """Bind the cache to a model type and base directory.

        Args:
            model_class: Pydantic model stored in this namespace; also
                determines the folder name.
            base_dir: Parent directory holding every model folder.
        """
        self._model_class = model_class
        self.base_dir = base_dir
        self.folder_path = os.path.join(self.base_dir, self._model_class.__name__)
        super().__init__()

    @abstractmethod
    def set(self, key: str, data: T, expiry_time: float) -> None:
        """Persist ``data`` under ``key`` until ``expiry_time``.

        Args:
            key: Lookup key — a page URL for company records, the raw
                query string for search results.
            data: Model instance (or list of them) to serialize.
            expiry_time: Absolute POSIX timestamp after which the entry
                is treated as expired.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> T | None:
        """Return the cached value for ``key``.

        Args:
            key: The lookup key used at :meth:`set` time.

        Returns:
            The deserialized model(s), or ``None`` on a miss or when
            the entry has expired.
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a single ``key`` from this model's namespace only."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Wipe this model's entire namespace without touching others."""
        pass
