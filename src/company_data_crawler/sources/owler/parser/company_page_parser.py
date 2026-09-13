"""Owler page parser: __NEXT_DATA__ initialState -> CompanyData.

Owler's Next.js state is a flat company dict (no reference graph, unlike
Craft): names, links, funding, leaders, competitors and industries are
read directly, with tolerant ``_safe_*`` converters for sloppy values.
"""

import json
from typing import Any, Optional

from company_data_crawler.base.parser import Parser
from company_data_crawler.models.company_data import (
    CompanyData,
    CompanyEmployeeCount,
    CompanyFundingInfo,
    CompanyLocation,
    CompanyStatus,
    CurrentCompanyStatus,
    KeyExecutive,
    OtherSocialMedia,
    SimilarCompany,
)
from company_data_crawler.utils.general_utils import GeneralUtils

RawData = dict[str, Any]


class OwlerParser(Parser):
    """Parser for Owler company page data.

    Converts raw Owler JSON data (from window.__NEXT_DATA__.props.initialState)
    into the standardized CompanyData model.
    """

    def _parse_basic_info(self, raw_data: RawData) -> CompanyData:
        """Extract basic company information."""
        linkedin_url = None
        twitter_url = None
        other_social_media: dict[OtherSocialMedia, str] = {}

        for link in raw_data.get("links", []):
            link_type = link.get("linkType", "").lower()
            link_url = link.get("link", "")
            if not link_url:
                continue
            if link_type == "facebook":
                other_social_media[OtherSocialMedia.FACEBOOK] = link_url
            elif link_type == "twitter":
                twitter_url = link_url
            elif link_type == "linkedin":
                linkedin_url = link_url

        status_info = raw_data.get("statusInfo", {})
        ownership = raw_data.get("ownership", "")
        status = status_info.get("status", "")

        return CompanyData(
            company_name=raw_data.get("companyName", ""),
            company_domain=raw_data.get("domainName", ""),
            company_description=raw_data.get("description", ""),
            company_logo_url=raw_data.get("logo", ""),
            company_founded_year=self._safe_int(raw_data.get("founded")),
            company_website_url=raw_data.get("website", raw_data.get("cpLink", "")),
            company_type=ownership if ownership else None,
            company_symbol=raw_data.get("ticker", ""),
            company_linkedin_url=linkedin_url,
            company_twitter_url=twitter_url,
            company_status=CurrentCompanyStatus(
                status=self._map_status(status, ownership),
                last_updated=GeneralUtils.get_current_date(),
            ),
            other_social_media_urls=other_social_media if other_social_media else None,
        )

    def _map_status(self, status: str, ownership: str) -> CompanyStatus:
        """Map Owler status to CompanyStatus enum."""
        status_lower = (status or "").lower()
        ownership_lower = (ownership or "").lower()

        if "subsidiary" in status_lower or "acquired" in status_lower:
            return CompanyStatus.ACQUIRED
        elif "closed" in status_lower or "defunct" in status_lower:
            return CompanyStatus.CLOSED
        elif "bankrupt" in status_lower:
            return CompanyStatus.BANKRUPT
        elif (
            ownership_lower == "public"
            or ownership_lower == "private"
            or ownership_lower
            and ownership_lower != ""
        ):
            return CompanyStatus.ACTIVE
        return CompanyStatus.UNKNOWN

    def _safe_int(self, value: Any) -> int | None:
        """Safely convert a value to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value: Any) -> float | None:
        """Convert ``value`` to float, returning ``None`` for missing/unparseable input instead of raising."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_employee_count(self, raw_data: RawData) -> list[CompanyEmployeeCount]:
        """Build the headcount series from Owler's ``employeeCount`` field (entries lacking a usable total are skipped)."""
        employee_counts = []
        count = raw_data.get("employeeCount")
        if count:
            employee_counts.append(
                CompanyEmployeeCount(
                    total_employees=self._safe_int(count) or 0,
                )
            )
        return employee_counts

    def _parse_key_executives(self, raw_data: RawData) -> list[KeyExecutive]:
        """Build leadership entries from Owler's CEO + leadership list (name/title plus LinkedIn/Twitter when present)."""
        executives = []

        # Parse CEO detail
        ceo_detail = raw_data.get("ceoDetail", {})
        if ceo_detail:
            first_name = ceo_detail.get("firstName", "")
            last_name = ceo_detail.get("lastName", "")
            name = f"{first_name} {last_name}".strip()
            if name:
                executives.append(
                    KeyExecutive(
                        name=name,
                        title=ceo_detail.get("designation", "CEO"),
                        linkedin_url=ceo_detail.get("linkedIn") or None,
                        twitter_url=ceo_detail.get("twitter") or None,
                    )
                )

        # Parse leadership details
        for leader in raw_data.get("leaderShipDetails", []):
            first_name = leader.get("firstName", "")
            last_name = leader.get("lastName", "")
            name = f"{first_name} {last_name}".strip()
            if name:
                executives.append(
                    KeyExecutive(
                        name=name,
                        title=leader.get("designation", ""),
                        linkedin_url=leader.get("linkedIn") or None,
                        twitter_url=leader.get("twitter") or None,
                    )
                )

        return executives

    def _parse_locations(self, raw_data: RawData) -> list[CompanyLocation]:
        """Extract location information."""
        locations = []
        city = raw_data.get("city", "")
        state = raw_data.get("state", "")
        country = raw_data.get("country", "")
        street = raw_data.get("street1Address", "")
        zipcode = raw_data.get("zipcode", "")

        if city or state or country:
            locations.append(
                CompanyLocation(
                    city=city if city else None,
                    state=state if state else None,
                    country=country if country else None,
                    address=street if street else None,
                    postal_code=zipcode if zipcode else None,
                    is_headquarter=True,
                )
            )
        return locations

    def _parse_funding_info(self, raw_data: RawData) -> list[CompanyFundingInfo]:
        """Extract funding information."""
        funding_info = []
        for funding in raw_data.get("companyFundingInfo", []):
            investors = [
                inv.get("name", "")
                for inv in funding.get("investorData", [])
                if inv.get("name")
            ]
            funding_info.append(
                CompanyFundingInfo(
                    funding_round=funding.get("fundingRound", "unknown"),
                    funding_amount=self._safe_float(funding.get("fundingAmount"))
                    or 0.0,
                    funding_date=funding.get("fundingDate"),
                    investors=investors,
                )
            )
        return funding_info

    def _parse_similar_companies(self, raw_data: RawData) -> list[SimilarCompany]:
        """Extract similar/competitor companies."""
        similar = []
        for competitor in raw_data.get("cg", []):
            basic_info = competitor.get("companyBasicInfo", {})
            company_name = basic_info.get("shortName", "")
            if company_name:
                similar.append(
                    SimilarCompany(
                        company_name=company_name,
                        company_industries=competitor.get("industrySectors", []),
                    )
                )
        return similar

    def _parse_industries(self, raw_data: RawData) -> list[str]:
        """Extract industry information."""
        # Prefer industrySectors, fall back to industries
        industries = raw_data.get("industrySectors", [])
        if industries:
            return industries
        return raw_data.get("industries", [])

    def parse(self, data: str) -> CompanyData:
        """Parse raw Owler JSON data into CompanyData model."""
        json_data = json.loads(data)

        # Get the company data from the state
        company_data = self._parse_basic_info(json_data)

        # Parse additional fields
        company_data.company_employee_counts = self._parse_employee_count(json_data)
        company_data.key_executives = self._parse_key_executives(json_data)
        company_data.company_locations = self._parse_locations(json_data)
        company_data.company_funding_info = self._parse_funding_info(json_data)
        company_data.similar_companies = self._parse_similar_companies(json_data)
        company_data.company_industries = self._parse_industries(json_data)

        return company_data
