from __future__ import annotations

import argparse
import json

from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver

from company_data_crawler.base.scraper import UrlScraper
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger

logger = get_logger(__name__)


class CraftSeleniumUrlScraper(UrlScraper):
    """Selenium-based URL scraper for Craft.co pages.

    Uses SeleniumBase UC mode to load JavaScript-rendered pages and
    extract window.App.cache data.
    """

    def __init__(self, *, headless: bool = False, page_load_timeout: int = 30) -> None:
        """Configure browser defaults (overridable per call via ``ICrawlerConfig``).

        Args:
            headless: Prefer headless Chrome. The effective value is
                ``headless or config.headless``, so config can force
                headless but never force a visible window.
            page_load_timeout: Seconds for page loads when no config is
                passed to :meth:`scrape`.
        """
        self.headless = headless
        self.page_load_timeout = page_load_timeout

    def build_proxies(self, proxy: str | None):
        """Build proxy configuration for Selenium."""
        if not proxy:
            return None
        return proxy

    def _build_driver_options(self, config: ICrawlerConfig | None) -> dict[str, object]:
        """Translate constructor + ``config`` into SeleniumBase ``Driver`` kwargs (UC mode, headless flag, optional proxy)."""
        driver_options: dict[str, object] = {
            "uc": config.uc if config is not None else True,
            "headless": self.headless
            or (config.headless if config is not None else False),
        }
        if config is not None and config.proxy:
            driver_options["proxy"] = config.proxy
        return driver_options

    def scrape(self, url: str, config: ICrawlerConfig | None = None) -> str:
        """Render ``url`` in UC-mode Chrome and return ``window.App.cache`` as JSON.

        Waits for ``document.readyState == "complete"``, reads the
        embedded cache via ``execute_script``, and always quits the
        driver. ``TypeError`` (unserializable/missing cache) and other
        failures are logged and re-raised for the chain to handle.

        Args:
            url: Craft company page URL.
            config: UC/headless/proxy/timeout settings.

        Returns:
            The embedded cache serialized as a JSON string.

        Raises:
            Exception: Render/extraction failures (after logging).
        """
        logger.info("Starting crawl: %s", url)
        request_timeout = (
            config.request_timeout if config is not None else self.page_load_timeout
        )

        driver = Driver(**self._build_driver_options(config))
        try:
            driver.set_page_load_timeout(request_timeout)
            driver.get(url)
            WebDriverWait(driver, request_timeout).until(
                lambda current_driver: current_driver.execute_script(
                    "return document.readyState"
                )
                == "complete"
            )
            logger.info("Finished crawl: %s", url)
            json_response = driver.execute_script("return window.App.cache")
            return json.dumps(json_response)

        except TypeError as ex:
            logger.exception(f"TypeError at scrape: {ex}")
            raise

        except Exception:
            logger.exception("Crawl failed: %s", url)
            raise
        finally:
            driver.quit()


def main() -> None:
    """CLI entry point: fetch one Craft URL with Selenium and print the JSON (``--headless`` supported)."""
    argument_parser = argparse.ArgumentParser(
        description="Fetch a Craft page with SeleniumBase UC mode."
    )
    argument_parser.add_argument("url", help="The page URL to fetch")
    argument_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome without opening a visible browser window",
    )
    arguments = argument_parser.parse_args()

    html = CraftSeleniumUrlScraper(headless=arguments.headless).scrape(arguments.url)
    print(html)


if __name__ == "__main__":
    main()
