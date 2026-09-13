from company_data_crawler.sources.base import SourceProvider


class SourceRegistry:
    """String-keyed registry of :class:`SourceProvider` implementations.

    Sources self-register via the :meth:`register` decorator. Consumers only
    ever deal with plain strings::

        provider = SourceRegistry.create("craft")
        provider = SourceRegistry.create("owler")   # once registered
    """

    _sources: dict[str, type[SourceProvider]] = {}

    @classmethod
    def register(cls, name: str):
        """Class decorator registering a SourceProvider under ``name``."""

        def decorator(provider_cls: type[SourceProvider]) -> type[SourceProvider]:
            """Validate, normalize and store one provider class.

            The source name is stripped/lowercased to make lookups
            case-insensitive; the class must expose ``search_company``
            and ``get_company_data``. Re-registering an existing key
            raises, and the normalized key is stamped back onto the
            class as ``source_name``.

            Raises:
                ValueError: On a bad name, a non-conforming class, or a
                    duplicate registration.
            """
            if not (
                isinstance(name, str)
                and name
                and hasattr(provider_cls, "search_company")
                and hasattr(provider_cls, "get_company_data")
            ):
                raise ValueError(
                    "SourceRegistry.register requires a source name and a "
                    "SourceProvider subclass."
                )
            key = name.strip().lower()
            if key in cls._sources:
                raise ValueError(
                    f"Source {key!r} is already registered "
                    f"({cls._sources[key].__name__})."
                )
            cls._sources[key] = provider_cls
            provider_cls.source_name = key
            return provider_cls

        return decorator

    @classmethod
    def create(cls, source: str, *args, **kwargs) -> SourceProvider:
        """Instantiate the provider registered under ``source``."""
        key = (source or "").strip().lower()
        if key not in cls._sources:
            raise ValueError(
                f"Unsupported source: {source!r}. "
                f"Available sources: {', '.join(cls.available_sources()) or 'none'}. "
                "Register your own with @SourceRegistry.register(<name>)."
            )
        return cls._sources[key](*args, **kwargs)

    @classmethod
    def get(cls, source: str) -> type[SourceProvider]:
        """Return the provider *class* registered under ``source``."""
        key = (source or "").strip().lower()
        if key not in cls._sources:
            raise ValueError(
                f"Unsupported source: {source!r}. "
                f"Available sources: {', '.join(cls.available_sources()) or 'none'}."
            )
        return cls._sources[key]

    @classmethod
    def available_sources(cls):
        """Sorted list of registered source names."""
        return sorted(cls._sources)
