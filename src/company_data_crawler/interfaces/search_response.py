from pydantic import BaseModel, Field
from typing import Optional


class ISearchResponse(BaseModel):
    """One company suggestion returned by a name search.

    Lightweight pointer to a canonical company page: the facade feeds
    ``source_url`` straight into ``get_company_data``. ``company_name``
    and ``slug`` are required (min length 1); ``logo_url`` is optional
    because not every source exposes a logo.
    """

    company_name: str = Field(min_length=1)
    source_url: str
    logo_url: str | None = None
    slug: str = Field(min_length=1)
