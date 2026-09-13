"""Central logging setup for the crawler.

All modules obtain their logger via :func:`get_logger`, which honours
two environment variables:

- ``CRAWLER_LOG_LEVEL`` (default ``"INFO"``): any stdlib level name.
- ``CRAWLER_LOG_FORMAT``: a :mod:`logging` format string.

Handlers are attached once per logger name and propagation to the root
logger is disabled, so library output never duplicates the host app's.
"""

from __future__ import annotations

import logging
import os

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a consistently configured logger for crawler modules.

    The first call for a given ``name`` attaches a single
    :class:`~logging.StreamHandler` (honouring ``CRAWLER_LOG_FORMAT``)
    and disables propagation; later calls only refresh the level from
    ``CRAWLER_LOG_LEVEL``.

    Args:
        name: Logger name, conventionally ``__name__`` or a friendly
            service label such as ``"Scraping Orchestrator"``.

    Returns:
        The configured :class:`logging.Logger`.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(os.getenv("CRAWLER_LOG_FORMAT", _DEFAULT_FORMAT))
        )
        logger.addHandler(handler)
        logger.propagate = False

    level_name = os.getenv("CRAWLER_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    return logger
