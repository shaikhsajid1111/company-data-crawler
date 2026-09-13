"""Craft page parser: window.App.cache reference-graph -> CompanyData.

Craft embeds a normalized store: the ``"Company:<id>"`` node holds the
company, while lists (tags, employees, locations, funding, executives,
competitors, income statements, metrics) are ``{"id", "typename"}``
references resolved against the same dict via :meth:`_resolve_reference`.
"""

import json
from typing import Any, Optional, TypeAlias

from company_data_crawler.base.parser import Parser
from company_data_crawler.global_utils.currency_parser import CurrencyParser
from company_data_crawler.global_utils.uri_utils import UriUtils
from company_data_crawler.models.company_data import (
    CompanyData,
    CompanyEmployeeCount,
    CompanyFundingInfo,
    CompanyLocation,
    CompanyOperatingMetric,
    CurrentCompanyStatus,
    IncomeStatement,
    KeyExecutive,
    OtherSocialMedia,
    SimilarCompany,
)
from company_data_crawler.utils.general_utils import GeneralUtils

RawData: TypeAlias = dict[str, Any]


class CraftParser(Parser):
    """Parse Craft's ``window.App.cache`` JSON into :class:`CompanyData`."""

    def _parse_basic_info(self, raw_data: dict[str, Any]) -> CompanyData:
        """Build the CompanyData skeleton: name, domain (from homepage), founded year, social links, status, description, logo, type and ticker."""
        homepage = raw_data.get("homepage", "")

        return CompanyData(
            company_name=raw_data.get("displayName", ""),
            company_domain=UriUtils.extract_domain_from_url(homepage),
            company_founded_year=raw_data.get("foundedYear"),
            company_linkedin_url=raw_data.get("linkedin", ""),
            company_twitter_url=raw_data.get("twitter", ""),
            company_status=CurrentCompanyStatus(
                status=GeneralUtils.handle_current_status(raw_data.get("status", "")),
                last_updated=GeneralUtils.get_current_date(),
            ),
            other_social_media_urls={
                OtherSocialMedia.INSTAGRAM: raw_data.get("instagram", ""),
                OtherSocialMedia.FACEBOOK: raw_data.get("facebook", ""),
                OtherSocialMedia.CRUNCHBASE: raw_data.get("crunchbase", ""),
            },
            company_description=raw_data.get("longDescription", ""),
            company_website_url=homepage,
            company_logo_url=raw_data.get("logo", {}).get("id", ""),
            company_type=raw_data.get("companyType"),
            company_symbol=raw_data.get("stockTicker", ""),
        )

    def _resolve_reference(
        self,
        reference: dict[str, Any],
        raw_data: dict[str, Any],
        expected_type: str,
    ) -> dict[str, Any] | None:
        """Dereference one ``{"id", "typename"}`` pointer from the normalized cache.

        Args:
            reference: Pointer object to resolve.
            raw_data: The whole cache dict keyed by reference id.
            expected_type: Required ``typename`` guard.

        Returns:
            The referenced node, or ``None`` on type mismatch, missing
            id, or absent target.
        """
        if reference.get("typename") != expected_type:
            return None

        reference_id = reference.get("id")

        if not reference_id:
            return None

        return raw_data.get(reference_id)

    def _parse_total_funding(
        self,
        company_data: RawData,
        raw_data: RawData,
    ) -> list[CompanyFundingInfo]:
        """Resolve the ``totalFunding`` pointer into a single aggregate funding entry (round ``"unknown"``, symbol mapped to an ISO code)."""
        funding_ref = company_data.get("totalFunding", {})
        funding_id = funding_ref.get("id")

        if not funding_id:
            return []

        funding = raw_data.get(funding_id)

        if not funding:
            return []

        currencies = CurrencyParser.get_codes_by_symbol(
            funding.get("currencySymbol", "")
        )

        return [
            CompanyFundingInfo(
                funding_round="unknown",
                funding_amount=funding.get("value", 0),
                funding_currency=currencies[0] if currencies else None,
            )
        ]

    def _parse_employee_count(
        self,
        company_data: dict[str, Any],
        raw_data: dict[str, Any],
    ) -> list[CompanyEmployeeCount]:
        """Resolve ``employees`` pointers into dated headcount entries (skips unresolvable refs)."""
        employee_counts = []

        for reference in company_data.get("employees", []):
            employee_data = self._resolve_reference(
                reference,
                raw_data,
                expected_type="EmployeeNumber",
            )

            if not employee_data:
                continue

            count = employee_data.get("employeeNumber")

            if count is None:
                continue
            date = GeneralUtils.parse_date(employee_data.get("date"))
            if date is None:
                continue
            employee_counts.append(
                CompanyEmployeeCount(
                    total_employees=count, month=date.month, year=date.year
                )
            )

        return employee_counts

    def _parse_key_executives(
        self, company_key_data: dict, raw_company_data: dict[str, Any]
    ) -> list[KeyExecutive]:
        """Resolve ``keyExecutives`` pointers into :class:`KeyExecutive` entries (skips unresolvable refs)."""
        parsed_key_executives: list[KeyExecutive] = []

        for executive_ref in company_key_data.get("keyExecutives", []):
            executive = self._resolve_reference(
                executive_ref,
                raw_company_data,
                "KeyExecutive",
            )

            if not executive:
                continue

            executive_name: Any = executive.get("name")
            executive_title: Any = executive.get("title")
            executive_linkedin: Any = executive.get("linkedin")
            executive_twitter: Any = executive.get("twitter")
            executive_facebook: Any = executive.get("facebook")
            other_social_media = (
                {OtherSocialMedia.FACEBOOK: executive_facebook}
                if executive_facebook
                else None
            )
            parsed_executive_data = KeyExecutive(
                name=executive_name,
                title=executive_title,
                linkedin_url=executive_linkedin,
                twitter_url=executive_twitter,
                other_social_media_urls=other_social_media,
            )
            parsed_key_executives.append(parsed_executive_data)
        return parsed_key_executives

    def _parse_locations(
        self,
        company_data: RawData,
        raw_data: RawData,
    ) -> list[CompanyLocation]:
        """Resolve ``locations`` pointers into :class:`CompanyLocation` entries, preserving the HQ flag."""
        locations = []

        for reference in company_data.get("locations", []):
            location = raw_data.get(reference.get("id"))

            if not location or location.get("__typename") != "Location":
                continue

            locations.append(
                CompanyLocation(
                    city=location.get("city", ""),
                    state=location.get("state", ""),
                    country=location.get("countryName"),
                    country_code=location.get("countryCode"),
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                    address=location.get("address", ""),
                    postal_code=None,
                    is_headquarter=location.get("hq", False),
                )
            )
        return locations

    def _parse_tags(
        self,
        tag_references: list[dict],
        raw_company_data: dict,
    ) -> list[str]:
        """Resolve tag pointers into lower-cased industry names (``company_industries``)."""
        tags = set()

        for reference in tag_references or []:
            tag = self._resolve_reference(
                reference,
                raw_company_data,
                expected_type="Tag",
            )

            if tag and tag.get("name"):
                tags.add(tag["name"].lower())

        return sorted(tags)

    def _parse_similar_companies(
        self,
        company_key_data: dict,
        raw_company_data: dict,
    ) -> list[SimilarCompany]:
        """Resolve ``competitors`` company pointers into name + industries pairs."""
        similar_companies = []

        for reference in company_key_data.get("competitors", []):
            company = self._resolve_reference(
                reference,
                raw_company_data,
                expected_type="Company",
            )

            if not company:
                continue

            similar_companies.append(
                SimilarCompany(
                    company_name=company.get("displayName"),
                    company_industries=self._parse_tags(
                        company.get("tags", []),
                        raw_company_data,
                    ),
                )
            )

        return similar_companies

    def _parse_income_statements(
        self,
        company_data: RawData,
        raw_data: RawData,
    ) -> list[IncomeStatement]:
        """Resolve income-statement pointers, joining each to its ``period`` node for end-date/period-type."""
        statements = []

        for reference in company_data.get("incomeStatements", []):
            statement_id = reference.get("id")

            if not statement_id:
                continue

            statement = raw_data.get(statement_id)

            if not statement:
                continue

            period_id = statement.get("period", {}).get("id")
            period = raw_data.get(period_id, {})

            statements.append(
                IncomeStatement(
                    revenue=statement.get("revenue"),
                    currency=statement.get("currencyIsoCode"),
                    net_income=statement.get("netIncome"),
                    gross_profit_margin=statement.get("grossProfitMargin"),
                    end_date=period.get("displayEndDate"),
                    period_type=period.get("periodType"),
                    ebitda=statement.get("ebit"),
                    gross_profit=statement.get("grossProfit"),
                )
            )

        return statements

    def _parse_operating_metrics(
        self,
        company_key_data: dict,
        raw_company_data: dict,
    ) -> list[CompanyOperatingMetric]:
        """Resolve ``operatingMetrics`` pointers, joining period (date) and Money (value) nodes into KPI entries."""
        operating_metrics = []

        for reference in company_key_data.get("operatingMetrics", []):
            metric = self._resolve_reference(
                reference,
                raw_company_data,
                expected_type="OperatingMetric",
            )

            if not metric:
                continue

            period = self._resolve_reference(
                metric.get("period", {}),
                raw_company_data,
                expected_type="Period",
            )

            value = self._resolve_reference(
                metric.get("value", {}),
                raw_company_data,
                expected_type="Money",
            )

            operating_metrics.append(
                CompanyOperatingMetric(
                    company_specific_kpi=metric.get("companySpecificKpi", ""),
                    metric_value=value.get("value") if value else None,
                    unit_type=metric.get("unitType"),
                    date=GeneralUtils.parse_date(
                        period.get("endDate") if period else None
                    ),
                )
            )

        return operating_metrics

    def parse(self, data: str) -> CompanyData:
        """Parse a ``window.App.cache`` JSON dump into a full CompanyData record.

        Locates the ``"Company:<id>"`` node via regex, builds the
        skeleton with :meth:`_parse_basic_info`, then fills every
        section (funding, executives, headcount, locations, tags,
        competitors, income statements, metrics).

        Args:
            data: JSON string of the normalized cache.

        Returns:
            The assembled :class:`CompanyData`.
        """
        json_data = json.loads(data)
        company_key_data: Any = GeneralUtils.search_data_by_key(
            json_data, r"^Company:\d+$"
        )
        company_data = self._parse_basic_info(company_key_data)
        company_data.company_funding_info = self._parse_total_funding(
            company_key_data, json_data
        )
        company_data.key_executives = self._parse_key_executives(
            company_key_data, json_data
        )
        company_data.company_employee_counts = self._parse_employee_count(
            company_key_data, json_data
        )
        company_data.company_locations = self._parse_locations(
            company_key_data, json_data
        )
        company_data.company_industries = self._parse_tags(
            company_key_data.get("tags"), json_data
        )
        company_data.similar_companies = self._parse_similar_companies(
            company_key_data, json_data
        )
        company_data.company_income_statements = self._parse_income_statements(
            company_key_data, json_data
        )
        company_data.company_operating_metrics = self._parse_operating_metrics(
            company_key_data, json_data
        )

        return company_data

        return similar_companies
