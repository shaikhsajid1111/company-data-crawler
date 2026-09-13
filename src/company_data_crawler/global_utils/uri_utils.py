from typing import Optional

import tldextract


class UriUtils:
    """URL/domain helpers shared by all sources."""

    @staticmethod
    def build_craft_source_page_url(slug: str) -> str:
        """Build the canonical Craft company URL for ``slug``.

        Args:
            slug: Craft page slug, e.g. ``"stripe"``.

        Returns:
            ``"https://craft.co/<slug>"`` — the URL later fed to
            ``get_company_data``.
        """
        return f"https://craft.co/{slug}"

    @staticmethod
    def extract_domain_from_url(url: str | None) -> str:
        """Extract the registrable domain from ``url`` via tldextract.

        Args:
            url: Any URL (or None/empty).

        Returns:
            The top domain under the public suffix (``"stripe.com"``),
            or ``""`` when ``url`` is missing.
        """
        if not url:
            return ""
        ext = tldextract.extract(url)
        return ext.top_domain_under_public_suffix
