"""Firmographic data model: every source returns this same schema.

The top-level :class:`CompanyData` aggregates funding, headcount time
series, locations, executives, competitors, operating metrics and
income statements. All fields tolerate missing source data via
sensible defaults, and nested models keep their own descriptions.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime, timezone


class CompanyFundingInfo(BaseModel):
    """One funding round: amount, currency, date and participating investors."""

    funding_round: str = Field(
        default="unknown", description="The funding round of the company"
    )
    funding_amount: float = Field(
        default=0.0, description="The funding amount of the company"
    )
    funding_currency: str | None = Field(
        default=None, description="The currency of the funding amount"
    )
    funding_date: str | None = Field(
        default=None, description="The date of the funding round"
    )
    investors: list[str] = Field(
        default_factory=list, description="List of investors in the funding round"
    )


class CompanyOperatingMetric(BaseModel):
    """A company-specific KPI snapshot (e.g. MAU) with value, unit and date."""

    company_specific_kpi: str = Field(default="", description="Company Specific KPIs")
    metric_value: float | None = Field(
        default=None, description="Metric value of the defined KPIs"
    )
    unit_type: str | None = Field(default=None, description="Unit type of the KPIs")
    date: datetime | None = Field(default=None, description="The date of the metric")


class CompanyStatus(Enum):
    """Lifecycle states a company can be in; defaults to UNKNOWN when the source is ambiguous."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ACQUIRED = "acquired"
    BANKRUPT = "bankrupt"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class CurrentCompanyStatus(BaseModel):
    """A :class:`CompanyStatus` value stamped with when it was observed."""

    status: CompanyStatus = Field(
        default=CompanyStatus.UNKNOWN, description="The status of the company"
    )
    last_updated: datetime | None = Field(
        default=None, description="The last updated date of the company status"
    )


class CompanyEmployeeCount(BaseModel):
    """Headcount datapoint; ``month``/``year`` locate it in time, together forming the employee-count time series."""

    total_employees: int = Field(..., description="The total number of employees")
    month: int | None = Field(
        default=None, description="The month of the employee count"
    )
    year: int | None = Field(default=None, description="The year of the employee count")


class OtherSocialMedia(Enum):
    """Social profiles beyond LinkedIn/Twitter, used as dict keys in ``other_social_media_urls``."""

    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    CRUNCHBASE = "crunchbase"


class KeyExecutive(BaseModel):
    """A person in company leadership: name, title and optional profile links."""

    name: str = Field(..., description="The name of the key executive")
    title: str = Field(..., description="The title of the key executive")
    linkedin_url: str | None = Field(
        default=None, description="The LinkedIn URL of the key executive"
    )
    twitter_url: str | None = Field(
        default=None, description="The twitter URL of the key executive"
    )
    other_social_media_urls: dict[OtherSocialMedia, str] | None = Field(
        default=None, description="Other social media URLs of the key executive"
    )


class CompanyLocation(BaseModel):
    """One office location; ``is_headquarter`` flags the HQ entry."""

    city: str | None = Field(
        default=None, description="The city of the company location"
    )
    state: str | None = Field(
        default=None, description="The state of the company location"
    )
    country: str | None = Field(
        default=None, description="The country of the company location"
    )
    country_code: str | None = Field(
        default=None, description="The country code of the company location"
    )
    postal_code: str | None = Field(
        default=None, description="The postal code of the company location"
    )
    address: str | None = Field(default=None, description="Office location")
    longitude: float | None = Field(
        default=None, description="The longitude of the company location"
    )
    latitude: float | None = Field(
        default=None, description="The latitude of the company location"
    )
    is_headquarter: bool | None = Field(
        default=False, description="Whether the location is a headquarter"
    )


class SimilarCompany(BaseModel):
    """A competitor: name plus its industry tags."""

    company_name: str = Field(..., description="The name of the similar company")
    company_industries: list[str] = Field(
        default_factory=list, description="The industries of the similar company"
    )


class IncomeStatement(BaseModel):
    """One reporting period of financials (revenue, margins, EBITDA, ...)."""

    revenue: float | None = Field(
        default=None, description="The revenue of the company"
    )
    currency: str | None = Field(
        default=None, description="The currency of the income statement"
    )
    net_income: float | None = Field(
        default=None, description="The net income of the company"
    )
    gross_profit_margin: float | None = Field(
        default=None, description="The gross profit margin of the company"
    )
    end_date: str | None = Field(default=None, description="The end date of the period")
    period_type: str | None = Field(default=None, description="The type of the period")
    ebitda: float | None = Field(default=None, description="The EBIT of the company")
    gross_profit: float | None = Field(
        default=None, description="The gross profit of the company"
    )


class CompanyData(BaseModel):
    """The validated firmographic record every source produces.

    All collections default to empty and all scalars to ``None``/``""``,
    so partially scraped pages still validate. ``company_name`` is the
    only required field; ``last_scraped_at`` is stamped in UTC
    automatically per record.
    """

    company_name: str = Field(..., description="The name of the company")
    company_domain: str = Field(default="", description="The domain of the company")
    company_industries: list[str] = Field(
        default_factory=list, description="The industries of the company"
    )
    company_founded_year: int | None = Field(
        default=None, description="The year the company was founded"
    )
    company_website_url: str | None = Field(
        default=None, description="The website URL of the company"
    )
    company_funding_info: list[CompanyFundingInfo] = Field(
        default_factory=list, description="The funding information of the company"
    )
    company_logo_url: str | None = Field(
        default=None, description="The logo URL of the company"
    )
    company_status: CurrentCompanyStatus = Field(
        default_factory=lambda: CurrentCompanyStatus(
            status=CompanyStatus.UNKNOWN, last_updated=None
        ),
        description="The status of the company",
    )
    company_description: str | None = Field(
        default="", description="The description of the company"
    )
    key_executives: list[KeyExecutive] = Field(
        default_factory=list, description="The key executives of the company"
    )
    company_type: str | None = Field(
        default=None, description="The type of the company (e.g., private, public)"
    )
    company_linkedin_url: str | None = Field(
        default=None, description="The LinkedIn URL of the company"
    )
    company_twitter_url: str | None = Field(
        default=None, description="The Twitter URL of the company"
    )
    company_symbol: str | None = Field(
        default=None, description="The stock symbol of the company"
    )
    company_operating_metrics: list[CompanyOperatingMetric] = Field(
        default_factory=list, description="The operating metrics of the company"
    )
    company_employee_counts: list[CompanyEmployeeCount] = Field(
        default_factory=list, description="The employee counts of the company"
    )
    company_locations: list[CompanyLocation] = Field(
        default_factory=list, description="The location information of the company"
    )
    similar_companies: list[SimilarCompany] = Field(
        default_factory=list, description="The similar companies"
    )
    other_social_media_urls: dict[OtherSocialMedia, str] | None = Field(
        default=None, description="Other social media URLs of the company"
    )
    company_income_statements: list[IncomeStatement] = Field(
        default_factory=list, description="Income statements"
    )
    last_scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="The timestamp when the data was last scraped",
    )
