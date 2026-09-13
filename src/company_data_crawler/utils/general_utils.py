"""Grab-bag helpers: JSON search, status/date normalization, cache TTLs, user agents."""

import re
from typing import Any, Optional
from company_data_crawler.models.company_data import CompanyStatus
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
from fake_headers import Headers


class GeneralUtils:
    @staticmethod
    def search_data_by_key(
        data: dict[str, Any], key_pattern: str
    ) -> dict[str, Any] | None:
        """Find the value of the first key in ``data`` matching ``key_pattern``.

        Matching uses :func:`re.match`, i.e. the pattern is anchored at
        the start of each key — pass anchored patterns such as
        ``r"^Company:\\d+$"`` to pick a single company node.

        Args:
            data: Flat dict to search (Craft's normalized cache).
            key_pattern: Regex pattern for the key.

        Returns:
            The matched value, or ``None`` when nothing matches.
        """
        for key, value in data.items():
            if re.match(key_pattern, key):
                return value
        return None

    @staticmethod
    def handle_current_status(current_str: str) -> CompanyStatus:
        """Map free-text status copy onto :class:`CompanyStatus`.

        Scans ``current_str`` case-insensitively for the first of
        active/inactive/acquired/bankrupt/closed/unknown and returns the
        matching enum member, defaulting to ``UNKNOWN``.

        Args:
            current_str: Raw status text from the source page.

        Returns:
            The best-matching :class:`CompanyStatus`.
        """
        # match with regex to find the status in the string
        # find the closest active match to the status in the string
        status_match = re.search(
            r"(active|inactive|acquired|bankrupt|closed|unknown)",
            current_str,
            re.IGNORECASE,
        )
        if status_match:
            status_str = status_match.group(1).lower()
            if status_str == "active":
                return CompanyStatus.ACTIVE
            elif status_str == "inactive":
                return CompanyStatus.INACTIVE
            elif status_str == "acquired":
                return CompanyStatus.ACQUIRED
            elif status_str == "bankrupt":
                return CompanyStatus.BANKRUPT
            elif status_str == "closed":
                return CompanyStatus.CLOSED
        return CompanyStatus.UNKNOWN

    @staticmethod
    def get_current_date() -> datetime:
        """Return the current UTC timestamp (used for ``last_updated`` stamps)."""
        return datetime.now(tz=timezone.utc)

    @staticmethod
    def parse_date(date_str: str | None) -> datetime | None:
        """Parse flexible date strings with ``dateutil``.

        Args:
            date_str: Any date representation, or None/empty.

        Returns:
            The parsed datetime, or ``None`` when input is missing.
            Unparseable strings raise ``dateutil``'s ``ParserError``.
        """
        if not date_str:
            return None
        return parse(date_str)

    @staticmethod
    def generate_time_from_now(days: int) -> datetime:
        """Compute the UTC datetime ``days`` in the future.

        Used with ``.timestamp()`` to derive cache-expiry timestamps
        from the ``*_cache_expiry_time_days`` config values.

        Args:
            days: TTL in days from now.

        Returns:
            Future timezone-aware datetime.
        """
        current_date = datetime.now(tz=timezone.utc)
        n_days_ahead_time = current_date + timedelta(days=days)
        return n_days_ahead_time

    @staticmethod
    def get_random_user_agent() -> str:
        """Generates a fresh random User-Agent string."""
        return Headers(headers=False).generate().get("User-Agent", "")
