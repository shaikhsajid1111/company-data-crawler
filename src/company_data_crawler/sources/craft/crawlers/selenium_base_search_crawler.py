import argparse
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver

from company_data_crawler.base.scraper import CompanyNameScraper
from company_data_crawler.interfaces.iconfig import ICrawlerConfig
from company_data_crawler.logger import get_logger
from company_data_crawler.sources.craft.utils import CraftScrapingUtils
from company_data_crawler.utils.scraping_utils import ScrapingUtils

logger = get_logger(__name__)


class SeleniumbaseSearchCrawler(CompanyNameScraper):
    """Name-search fallback: type into Craft's search box in UC-mode Chrome and capture the GraphQL response off the wire via CDP performance logs."""

    def __init__(self, *, headless: bool = False, page_load_timeout: int = 30) -> None:
        """Configure browser defaults (see :class:`CraftSeleniumUrlScraper` for headless/timeout semantics)."""
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
    def _graphql_response_body(driver, timeout: float) -> str:
        """Wait for and return the UniversalSearch GraphQL response body.

        Polls CDP performance logs, tracking ``Network.responseReceived``
        for the search endpoint and resolving the body on the matching
        ``Network.loadingFinished`` via ``Network.getResponseBody``.

        Args:
            driver: Live SeleniumBase driver on the search page.
            timeout: Seconds to wait for the XHR round-trip.

        Returns:
            Raw response body string.
        """
        graphql_url = CraftScrapingUtils.get_search_query_url()
        response_ids: set[str] = set()
        response_urls: dict[str, str] = {}

        def find_response_body(_driver):
            for entry in _driver.get_log("performance"):
                message = json.loads(entry["message"])["message"]
                method = message["method"]
                params = message.get("params", {})

                if method == "Network.responseReceived":
                    response = params["response"]
                    if response["url"] == graphql_url:
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
                    if response_urls.pop(request_id, None) == graphql_url:
                        return body["body"]
            return False

        response_body = WebDriverWait(driver, timeout).until(find_response_body)
        return str(response_body)

    def scrape(self, query: str, config: ICrawlerConfig | None = None) -> str:
        """Type ``query`` into the search box and return the captured GraphQL payload.

        Drains the performance log first (to avoid stale entries), types
        human-style via :func:`ScrapingUtils.enter_keys_to_element`,
        then intercepts the response. List-wrapped payloads are
        unwrapped to their first element; empty results become an
        explicit ``{"data": {"universalSearch": []}}`` envelope.

        Args:
            query: Free-text company name.
            config: UC/headless/proxy/timeout settings.

        Returns:
            Raw GraphQL response body as a JSON string.

        Raises:
            Exception: Render/typing/capture failures (after logging).
        """
        url = CraftScrapingUtils.build_craft_page_url()
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
            response_body = self._graphql_response_body(driver, request_timeout)
            logger.info("Captured Craft GraphQL response for query: %s", query)
            data = json.loads(response_body)
            if not isinstance(data, list) or not data:
                return json.dumps({"data": {"universalSearch": []}})
            return json.dumps(data[0])
        except Exception as ex:
            logger.exception(
                f"Error while scraping company name using seleniumbase: {ex}"
            )
            raise
        finally:
            driver.quit()


def main() -> None:
    """CLI entry point: search Craft for one company name and print the raw GraphQL response (``--headless`` supported)."""
    argument_parser = argparse.ArgumentParser(
        description="Fetch a Craft company name with SeleniumBase UC mode."
    )
    argument_parser.add_argument("query", help="The company name to search for")
    argument_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome without opening a visible browser window",
    )
    arguments = argument_parser.parse_args()

    response = SeleniumbaseSearchCrawler(headless=arguments.headless).scrape(
        arguments.query, None
    )
    print(response)


if __name__ == "__main__":
    main()
