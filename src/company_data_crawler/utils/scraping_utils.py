import random
import time
from typing import Any


class ScrapingUtils:
    """Generic scraping utilities shared across all sources."""

    @staticmethod
    def enter_keys_to_element(element: Any, query: str) -> None:
        """Simulate human-like typing into a Selenium input element.

        Clicks and clears the field, then sends ``query`` one character
        at a time with a small random pause (60–180 ms) so
        keystroke-driven autocomplete/search requests fire naturally.

        Args:
            element: Selenium input element to type into.
            query: Text to type.
        """
        element.click()
        element.clear()
        for char in query:
            element.send_keys(char)
            time.sleep(random.uniform(0.06, 0.18))

    @staticmethod
    def prepare_default_headers() -> dict:
        """Return generic browser headers suitable for most websites."""
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '"Not=A?Brand";v="99", "Chromium";v="122", "Google Chrome";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }
