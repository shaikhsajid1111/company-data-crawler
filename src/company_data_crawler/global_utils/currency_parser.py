"""Money helpers: split free-text amounts into (value, ISO currency code)."""

from typing import Optional, TypedDict

from babel import Locale
from babel.numbers import get_currency_symbol
from price_parser import Price


class IAmountData(TypedDict):
    """Parsed money: numeric ``amount`` plus ISO ``currency`` code (either may be None when unresolvable)."""

    amount: float | None
    currency: str | None


class CurrencyParser:
    """Parse human-written money strings using price-parser + Babel."""

    @staticmethod
    def parse_amount_and_currency(string: str) -> IAmountData:
        """Split ``string`` into amount and currency code.

        The amount comes from ``price-parser``; the detected currency
        symbol is resolved to an ISO code via :meth:`get_codes_by_symbol`
        (first match wins). Falls back to the raw symbol when no ISO
        code matches, e.g. for unknown symbols.

        Args:
            string: Free text such as ``"$12M"`` or ``"€500"``.

        Returns:
            ``{"amount": float|None, "currency": str|None}``.
        """
        price = Price.fromstring(string)
        currency_symbol = price.currency
        currency_code = CurrencyParser.get_codes_by_symbol(currency_symbol)
        parsed_data = IAmountData(
            amount=price.amount_float,
            currency=currency_code[0] if currency_code else currency_symbol,
        )
        return parsed_data

    @staticmethod
    def get_codes_by_symbol(symbol: str | None, locale_str: str = "en") -> list:
        """Find ISO currency codes whose locale symbol equals ``symbol``.

        Iterates every currency in the Babel locale and collects codes
        whose preferred symbol matches exactly (e.g. ``"$"`` matches
        USD plus other dollar currencies — hence a list).

        Args:
            symbol: Currency symbol to look up; blank/None yields ``[]``.
            locale_str: Babel locale used for symbol resolution.

        Returns:
            Sorted, de-duplicated ISO codes (possibly empty).
        """
        if not symbol:
            return []
        search_symbol = symbol.strip()
        locale = Locale.parse(locale_str)
        matched_codes = []

        # Iterate through all standard currency codes in the locale
        for code in locale.currencies.keys():
            # Get the preferred symbol for each code
            if get_currency_symbol(code, locale=locale) == search_symbol:
                matched_codes.append(code)

        return sorted(list(set(matched_codes)))
