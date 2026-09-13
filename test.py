"""Offline test suite for company-data-crawler.

Run with:

    uv run python test.py

No network access or browser is required: every crawler is replaced with an
in-memory fake, so the tests exercise the whole pipeline deterministically
(search -> parse -> scrape -> cache -> source-registry string dispatch).
"""

import json
import tempfile
import time
import traceback

from company_data_crawler import (
    CompanyDataCrawler,
    CompanyData,
    ICrawlerConfig,
    IQuery,
    ISearchResponse,
    SourceProvider,
    SourceRegistry,
    register_source,
)
from company_data_crawler.base.searcher import CompanySearcher
from company_data_crawler.orchestrators.search_orchestrator import (
    CompanySearchingService,
)
from company_data_crawler.base.scraper import CompanyNameScraper, UrlScraper
from company_data_crawler.sources.craft.parsers.company_page_parser import (
    CraftParser,
)
from company_data_crawler.sources.craft.parsers.search_result_parser import (
    CraftSearchParser,
)
from company_data_crawler.sources.craft.provider import CraftSource
from company_data_crawler.models.ticker_resolution import TickerResolution
from company_data_crawler.searchers.yahoo_finance_ticker_resolver import (
    YahooFinanceTickerResolver,
)
from company_data_crawler.storage.persistent_disk_cache import DiskCache

# --------------------------------------------------------------------------
# Fakes: canned Craft responses + scrapers that never touch the network.
# --------------------------------------------------------------------------

CRAFT_SEARCH_RESPONSE = json.dumps(
    {
        "data": {
            "universalSearch": [
                {
                    "company": {
                        "displayName": "Stripe",
                        "slug": "stripe",
                        "logo": {"url": "https://logo.example.com/stripe.png"},
                        "__typename": "Company",
                    },
                    "__typename": "SearchSuggestion",
                },
                {
                    "company": {
                        "displayName": "Stripe Atlas",
                        "slug": "stripe-atlas",
                        "logo": None,
                        "__typename": "Company",
                    },
                    "__typename": "SearchSuggestion",
                },
            ]
        }
    }
)

CRAFT_COMPANY_CACHE = json.dumps(
    {
        "Company:123": {
            "displayName": "TestCo",
            "homepage": "https://test.example.com",
            "foundedYear": 2001,
            "status": "Operating",
            "tags": [{"id": "tag1", "typename": "Tag"}],
            "employees": [{"id": "emp1", "typename": "EmployeeNumber"}],
            "locations": [{"id": "loc1", "typename": "Location"}],
            "totalFunding": {"id": "fund1"},
            "keyExecutives": [{"id": "kex1", "typename": "KeyExecutive"}],
            "competitors": [{"id": "Company:999", "typename": "Company"}],
            "incomeStatements": [{"id": "inc1"}],
            "operatingMetrics": [{"id": "om1", "typename": "OperatingMetric"}],
        },
        "tag1": {"name": "Software"},
        "emp1": {"employeeNumber": 1234, "date": "2024-01-15"},
        "loc1": {
            "city": "SF",
            "countryName": "USA",
            "countryCode": "US",
            "address": "1 Main St",
            "hq": True,
            "__typename": "Location",
        },
        "fund1": {"value": 12000000, "currencySymbol": "$"},
        "kex1": {"name": "Jane Doe", "title": "CEO"},
        "Company:999": {
            "displayName": "RivalCo",
            "tags": [{"id": "tag1", "typename": "Tag"}],
        },
        "inc1": {"revenue": 500.5, "currencyIsoCode": "USD", "period": {"id": "p1"}},
        "p1": {"displayEndDate": "2023-12-31", "periodType": "FY"},
        "om1": {
            "companySpecificKpi": "MAU",
            "unitType": "users",
            "period": {"id": "p1"},
            "value": {"id": "v1", "typename": "Money"},
        },
        "v1": {"value": 99.5},
    }
)


class FakeCraftSearchScraper(CompanyNameScraper):
    """Returns a canned Craft GraphQL search response (no network)."""

    def __init__(self) -> None:
        self.calls = []

    def scrape(self, query, config=None) -> str:
        self.calls.append(query)
        return CRAFT_SEARCH_RESPONSE


class FakeCraftUrlScraper(UrlScraper):
    """Returns a canned Craft window.App.cache payload (no network)."""

    def __init__(self) -> None:
        self.calls = []

    def build_proxies(self, proxy):
        return None

    def scrape(self, url, config=None) -> str:
        self.calls.append(url)
        return CRAFT_COMPANY_CACHE


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_company_data_defaults():
    """Adjusted CompanyData: fresh per-instance timestamps, sane defaults."""
    a = CompanyData(company_name="A")
    time.sleep(0.01)
    b = CompanyData(company_name="B")
    assert (
        a.last_scraped_at != b.last_scraped_at
    ), "last_scraped_at must be per-instance"
    assert a.company_status.status.value == "unknown"
    assert a.company_founded_year is None
    assert a.company_industries == []
    assert a.company_funding_info == []
    assert a.company_locations == []


def test_craft_parser_parses_full_payload():
    """CraftParser maps the raw window.App.cache payload onto CompanyData."""
    company = CraftParser().parse(CRAFT_COMPANY_CACHE)
    assert company.company_name == "TestCo"
    assert company.company_domain == "example.com"  # tldextract strips subdomain
    assert company.company_industries == ["software"]
    assert company.company_founded_year == 2001
    assert company.company_employee_counts[0].total_employees == 1234
    assert company.company_locations[0].city == "SF"
    assert company.company_locations[0].is_headquarter is True
    assert company.company_funding_info[0].funding_amount == 12000000
    assert company.company_funding_info[0].funding_currency == "USD"
    assert company.key_executives[0].name == "Jane Doe"
    assert company.similar_companies[0].company_name == "RivalCo"
    assert company.company_income_statements[0].revenue == 500.5
    assert company.company_operating_metrics[0].metric_value == 99.5
    assert (
        company.company_status.status.value == "unknown"
    )  # "Operating" has no keyword match


def test_disk_cache_round_trip():
    """Parsed CompanyData survives a persist -> load cycle."""
    company = CraftParser().parse(CRAFT_COMPANY_CACHE)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiskCache(CompanyData, tmp)
        cache.set("stripe", company, expiry_time=9999999999)
        loaded = cache.get("stripe")
        assert loaded.company_name == "TestCo"
        assert loaded.company_locations[0].is_headquarter is True
        cache.delete("stripe")
        assert cache.get("stripe") is None


def test_craft_search_flow_with_fake_scraper():
    """Search: fake scraper -> CraftSearchParser -> ISearchResponse + caching."""
    fake = FakeCraftSearchScraper()
    with tempfile.TemporaryDirectory() as tmp:
        source = CraftSource(cache_dir=tmp, searcher=fake)
        results = source.search_company("stripe", ICrawlerConfig(force_rescrape=True))
        assert len(results) == 2
        assert isinstance(results[0], ISearchResponse)
        assert results[0].company_name == "Stripe"
        assert results[0].source_url == "https://craft.co/stripe"
        assert results[1].slug == "stripe-atlas"
        assert fake.calls == ["stripe"]

        # Second call (no force_rescrape) is served from the disk cache.
        cached = source.search_company("stripe")
        assert [r.slug for r in cached] == ["stripe", "stripe-atlas"]
        assert fake.calls == ["stripe"], "second search must be cached"

        # force_rescrape bypasses the cache.
        source.search_company("stripe", ICrawlerConfig(force_rescrape=True))
        assert fake.calls == ["stripe", "stripe"]


def test_craft_scrape_flow_with_fake_scraper():
    """Scrape: fake scraper -> CraftParser -> CompanyData + caching."""
    fake = FakeCraftUrlScraper()
    with tempfile.TemporaryDirectory() as tmp:
        source = CraftSource(cache_dir=tmp, url_scraper=fake)
        company = source.get_company_data(
            "https://craft.co/stripe", ICrawlerConfig(force_rescrape=True)
        )
        assert company.company_name == "TestCo"
        assert fake.calls == ["https://craft.co/stripe"]

        # Second call is served from the disk cache -> no extra scrape.
        cached = source.get_company_data("https://craft.co/stripe")
        assert cached.company_name == "TestCo"
        assert fake.calls == ["https://craft.co/stripe"]

        # force_rescrape bypasses the cache.
        source.get_company_data(
            "https://craft.co/stripe", ICrawlerConfig(force_rescrape=True)
        )
        assert fake.calls == ["https://craft.co/stripe"] * 2


def test_registry_rejects_unknown_source():
    """Unknown source strings fail with a helpful message."""
    try:
        SourceRegistry.create("does-not-exist")
    except ValueError as ex:
        assert "does-not-exist" in str(ex)
        assert "craft" in str(ex)  # lists available sources
    else:
        raise AssertionError("SourceRegistry.create should reject unknown sources")

    assert "craft" in SourceRegistry.available_sources()


def test_custom_source_string_dispatch():
    """Prove pluggability: register a mock 'owler' source, select it by string.

    This is exactly how a real Owler/Crunchbase source plugs in: implement
    SourceProvider, register it with a string, and the facade accepts it.
    """

    if "owler_mock" not in SourceRegistry.available_sources():

        @register_source("owler_mock")
        class OwlerMockSource(SourceProvider):
            """Mock Owler: reuses Craft parsers with canned payloads."""

            def __init__(self, cache_dir=None, **kwargs) -> None:
                self.cache_dir = cache_dir

            def search_company(self, query, config=None):
                return CraftSearchParser().parse(CRAFT_SEARCH_RESPONSE)

            def get_company_data(self, url, config=None):
                return CraftParser().parse(CRAFT_COMPANY_CACHE)

    crawler = CompanyDataCrawler(cache_dir=tempfile.mkdtemp())
    assert "craft" in crawler.available_sources()
    assert "owler_mock" in crawler.available_sources()

    # Search + scrape on the custom source, purely via string dispatch.
    results = crawler.search_company("stripe", source="owler_mock")
    assert results[0].company_name == "Stripe"

    company = crawler.get_company_data(
        "https://owler.example.com/stripe", source="owler_mock"
    )
    assert company.company_name == "TestCo"

    # End-to-end: search by name then scrape the first result.
    by_name = crawler.get_company_data_by_name("stripe", source="owler_mock")
    assert by_name.company_name == "TestCo"

    # A source that is not registered yet is rejected by the facade too.
    try:
        crawler.get_company_data("https://x.example.com", source="crunchbase")
    except ValueError as ex:
        assert "crunchbase" in str(ex)
    else:
        raise AssertionError("crunchbase should not be registered yet")


def test_facade_provider_caching_and_case_insensitivity():
    """Providers are created once per source; source names are case-insensitive."""
    crawler = CompanyDataCrawler(cache_dir=tempfile.mkdtemp())
    provider = crawler._get_provider("craft")
    assert isinstance(provider, CraftSource)
    assert crawler._get_provider("craft") is provider
    assert crawler._get_provider("CRAFT") is provider  # normalized


def test_search_cache_namespaced_per_source():
    """Same query + shared cache dir must never leak between sources.

    Regression test: the search cache used to key entries by the raw query
    string alone, so a second source (owler) served the first source's
    (craft) cached suggestions for the identical query. Keys are now
    namespaced as "<source_name>:<query>".
    """

    class FakeSearcher(CompanySearcher):
        """Canned CompanySearcher returning one fixed suggestion."""

        def __init__(self, company_name: str, source_url: str) -> None:
            self.company_name = company_name
            self.source_url = source_url
            self.calls = []

        def search_by_name(self, name, config=None):
            self.calls.append(name)
            return [
                ISearchResponse(
                    company_name=self.company_name,
                    source_url=self.source_url,
                    slug=name.lower(),
                )
            ]

        def search_by_symbol(self, symbol, config=None):
            raise NotImplementedError

    craft_searcher = FakeSearcher("Apple (Craft)", "https://craft.co/apple")
    owler_searcher = FakeSearcher(
        "Apple (Owler)", "https://www.owler.com/company/apple"
    )

    with tempfile.TemporaryDirectory() as tmp:
        craft_service = CompanySearchingService(
            searcher=craft_searcher, source_name="craft", cache_dir=tmp
        )
        owler_service = CompanySearchingService(
            searcher=owler_searcher, source_name="owler", cache_dir=tmp
        )

        config = ICrawlerConfig()

        # First call per source: each serves its own fresh results.
        craft_first = craft_service.search_company(IQuery(company_name="apple"), config)
        owler_first = owler_service.search_company(IQuery(company_name="apple"), config)
        assert craft_first[0].source_url == "https://craft.co/apple"
        assert owler_first[0].source_url == "https://www.owler.com/company/apple"

        # Each searcher was hit exactly once — owler did NOT get craft's
        # cached entry for the identical query.
        assert craft_searcher.calls == ["apple"]
        assert owler_searcher.calls == ["apple"]

        # Second call per source: cache hits, still per source.
        craft_cached = craft_service.search_company(
            IQuery(company_name="apple"), config
        )
        owler_cached = owler_service.search_company(
            IQuery(company_name="apple"), config
        )
        assert craft_cached[0].source_url == "https://craft.co/apple"
        assert owler_cached[0].source_url == "https://www.owler.com/company/apple"
        assert craft_searcher.calls == ["apple"]  # no extra network calls
        assert owler_searcher.calls == ["apple"]

        # The raw query alone is no longer a valid cache key; entries live
        # only under the "<source>:<query>" namespace.
        shared_cache = DiskCache(ISearchResponse, tmp)
        assert shared_cache.get("apple") is None
        assert shared_cache.get("craft:apple") is not None
        assert shared_cache.get("owler:apple") is not None


def test_facade_symbol_search_delegates_to_provider():
    """search_company_by_symbol resolves the ticker, then runs the name search.

    The Yahoo resolver is replaced with a fake, so the test stays offline and
    only proves the facade -> SourceProvider.search_company_by_symbol wiring.
    """
    import company_data_crawler.sources.base as base_module

    if "symbol_mock" not in SourceRegistry.available_sources():

        @register_source("symbol_mock")
        class SymbolMockSource(SourceProvider):
            """Records the query it receives; returns canned Craft results."""

            def __init__(self, cache_dir=None, **kwargs) -> None:
                self.seen_queries = []

            def search_company(self, query, config=None):
                self.seen_queries.append(query)
                return CraftSearchParser().parse(CRAFT_SEARCH_RESPONSE)

            def get_company_data(self, url, config=None):
                return CraftParser().parse(CRAFT_COMPANY_CACHE)

    class FakeTickerResolver:
        def __init__(self, cache_dir=None):
            self.cache_dir = cache_dir

        def resolve(self, symbol, config=None):
            assert symbol.strip().upper() == "MSFT"
            return "Microsoft"

    original_resolver = base_module.YahooFinanceTickerResolver
    base_module.YahooFinanceTickerResolver = FakeTickerResolver
    try:
        crawler = CompanyDataCrawler(cache_dir=tempfile.mkdtemp())

        results = crawler.search_company_by_symbol("msft", source="symbol_mock")
        assert results[0].company_name == "Stripe"

        provider = crawler._get_provider("symbol_mock")
        assert provider.seen_queries == ["Microsoft"]

        company = crawler.get_company_data_by_symbol("MSFT", source="symbol_mock")
        assert company is not None
        assert company.company_name == "TestCo"

        # An empty ticker is rejected before any resolution/network work.
        try:
            crawler.search_company_by_symbol("   ", source="symbol_mock")
        except ValueError:
            pass
        else:
            raise AssertionError("empty ticker must raise ValueError")
    finally:
        base_module.YahooFinanceTickerResolver = original_resolver


def test_ticker_resolver_persistent_cache():
    """Yahoo ticker resolutions persist on disk across resolver instances."""
    with tempfile.TemporaryDirectory() as tmp:
        resolver = YahooFinanceTickerResolver(cache_dir=tmp)
        calls = []

        def fake_fetch(symbol, config=None):
            calls.append(symbol)
            return "Microsoft Corporation"

        resolver._fetch_company_name = fake_fetch

        # First call hits the (faked) network and caches the resolution.
        assert resolver.resolve("msft") == "Microsoft Corporation"
        assert calls == ["MSFT"]

        # Second call on the same instance is served from the disk cache.
        assert resolver.resolve("MSFT") == "Microsoft Corporation"
        assert calls == ["MSFT"]

        # A brand-new resolver sharing cache_dir also hits the cache.
        second = YahooFinanceTickerResolver(cache_dir=tmp)
        second._fetch_company_name = fake_fetch
        assert second.resolve(" MSFT ") == "Microsoft Corporation"
        assert calls == ["MSFT"]

        # The persisted record round-trips as a TickerResolution.
        entry = DiskCache(TickerResolution, tmp).get("MSFT")
        assert entry.ticker == "MSFT"
        assert entry.company_name == "Microsoft Corporation"

        # force_rescrape bypasses the cache and refreshes the entry.
        assert (
            resolver.resolve("msft", ICrawlerConfig(force_rescrape=True))
            == "Microsoft Corporation"
        )
        assert calls == ["MSFT", "MSFT"]

        # Empty tickers are rejected before any network/cache work.
        try:
            resolver.resolve("   ")
        except ValueError:
            pass
        else:
            raise AssertionError("empty ticker must raise ValueError")


def main() -> None:
    tests = [
        test_company_data_defaults,
        test_craft_parser_parses_full_payload,
        test_disk_cache_round_trip,
        test_craft_search_flow_with_fake_scraper,
        test_craft_scrape_flow_with_fake_scraper,
        test_registry_rejects_unknown_source,
        test_custom_source_string_dispatch,
        test_facade_provider_caching_and_case_insensitivity,
        test_facade_symbol_search_delegates_to_provider,
        test_ticker_resolver_persistent_cache,
        test_search_cache_namespaced_per_source,
    ]

    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except Exception:
            failures += 1
            print(f"FAIL  {test.__name__}")
            traceback.print_exc()

    print()
    if failures:
        print(f"{failures}/{len(tests)} test(s) FAILED")
        raise SystemExit(1)
    print(f"All {len(tests)} tests passed")


if __name__ == "__main__":
    main()
