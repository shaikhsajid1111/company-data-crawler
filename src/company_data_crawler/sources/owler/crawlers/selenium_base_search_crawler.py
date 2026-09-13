import argparse
import json
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver

from company_data_crawler.base.scraper import CompanyNameScraper
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger
from company_data_crawler.utils.scraping_utils import ScrapingUtils

logger = get_logger(__name__)


class OwlerSeleniumSearchCrawler(CompanyNameScraper):
    """Selenium-based search crawler for Owler.com.

    Uses SeleniumBase UC mode to load the page, intercepts the network
    request to the search API (basicSearchInternal), and returns the response.
    """

    def __init__(self, *, headless: bool = False, page_load_timeout: int = 30) -> None:
        """Configure browser defaults (see :class:`OwlerSeleniumUrlScraper` for headless/timeout semantics)."""
        self.headless = headless
        self.page_load_timeout = page_load_timeout

    def _build_driver_options(self, config: ICrawlerConfig | None) -> dict[str, object]:
        """Driver kwargs for search capture: UC mode, headless flag, proxy, plus ``log_cdp_events`` so network traffic is observable."""
        driver_options: dict[str, object] = {
            "uc": config.uc if config is not None else True,
            "headless": self.headless
            or (config.headless if config is not None else False),
            "log_cdp_events": True,
        }
        if config is not None and config.proxy:
            driver_options["proxy"] = config.proxy
        return driver_options

    @staticmethod
    def _intercept_search_response(driver, timeout: float) -> str:
        """Wait for and return the ``basicSearchInternal`` API response body.

        Polls CDP performance logs, tracking ``Network.responseReceived``
        entries whose URL contains the search-API path and resolving the
        body on the matching ``Network.loadingFinished`` via
        ``Network.getResponseBody``.

        Args:
            driver: Live SeleniumBase driver on owler.com.
            timeout: Seconds to wait for the XHR round-trip.

        Returns:
            Raw search API response body string.
        """
        search_api_pattern = "/a/v1/pb/basicSearchInternal"
        response_ids: set[str] = set()
        response_urls: dict[str, str] = {}

        def find_response_body(_driver):
            for entry in _driver.get_log("performance"):
                message = json.loads(entry["message"])["message"]
                method = message["method"]
                params = message.get("params", {})

                if method == "Network.responseReceived":
                    response = params["response"]
                    if search_api_pattern in response["url"]:
                        request_id = params["requestId"]
                        response_ids.add(request_id)
                        response_urls[request_id] = response["url"]
                elif (
                    method == "Network.loadingFinished"
                    and params["requestId"] in response_ids
                ):
                    request_id = params["requestId"]
                    body = _driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": request_id}
                    )
                    if search_api_pattern in response_urls.pop(request_id, ""):
                        return body["body"]
            return False

        response_body = WebDriverWait(driver, timeout).until(find_response_body)
        return str(response_body)

    def scrape(self, query: str, config: ICrawlerConfig | None = None) -> str:
        """Type ``query`` into the homepage search box and return the intercepted API response.

        Drains the performance log first (to avoid stale entries), types
        human-style via :func:`ScrapingUtils.enter_keys_to_element`,
        then intercepts the XHR body.

        Args:
            query: Free-text company name.
            config: UC/headless/proxy/timeout settings.

        Returns:
            Raw search API response body.

        Raises:
            Exception: Render/typing/capture failures (after logging).
        """
        url = "https://www.owler.com"
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
            driver.get_log("performance")
            search_box = driver.find_element(By.CSS_SELECTOR, "input[type=search]")
            ScrapingUtils.enter_keys_to_element(search_box, query)
            response_body = self._intercept_search_response(driver, request_timeout)
            logger.info("Captured Owler search API response for query: %s", query)
            return response_body
        except Exception as ex:
            logger.exception(
                f"Error while scraping company name using seleniumbase: {ex}"
            )
            raise
        finally:
            driver.quit()


def main() -> None:
    """CLI entry point: search Owler for one company name and print the raw API response (``--headless`` supported)."""
    argument_parser = argparse.ArgumentParser(
        description="Search Owler for a company name with SeleniumBase UC mode."
    )
    argument_parser.add_argument("query", help="The company name to search for")
    argument_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome without opening a visible browser window",
    )
    arguments = argument_parser.parse_args()

    response = OwlerSeleniumSearchCrawler(headless=arguments.headless).scrape(
        arguments.query, None
    )
    print(response)


if __name__ == "__main__":
    main()
