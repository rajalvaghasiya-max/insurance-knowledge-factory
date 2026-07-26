"""
life_intelligence_lab.validation
=================================

Pure validation functions for AMFI NAV row fields.

Every function either returns a normalized value or raises a
`ValidationError` carrying a short, stable, machine-readable reason code
(used verbatim in `RejectedRow.reason`). Nothing in this module guesses,
forward-fills, or infers a value that was not present in the source row.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


class ValidationError(Exception):
    """Raised with a short, stable reason code as the message."""


# AMFI scheme codes are numeric identifiers. Real-world codes are commonly
# 4-6 digits; the bound below is intentionally a little generous rather
# than over-fitted to today's exact digit count.
_SCHEME_CODE_RE = re.compile(r"^\d{2,8}$")

# AMFI publishes NAV dates as "DD-Mon-YYYY", e.g. "25-Jul-2026".
_NAV_DATE_FORMAT = "%d-%b-%Y"

# Values AMFI (and similar sources) use to mean "no ISIN" rather than an
# actual malformed value. These are treated as legitimately absent, not
# as an error.
_ISIN_ABSENT_TOKENS = {"-", "", "n.a.", "na", "n/a"}

# A real ISIN is 12 characters: 2-letter country code + 9 alphanumeric +
# 1 numeric check digit. We validate the shape loosely (12 alnum chars)
# rather than the full check-digit algorithm, since the purpose here is
# to catch obviously malformed values, not to be an ISIN authority.
_ISIN_SHAPE_RE = re.compile(r"^[A-Z0-9]{12}$")


def validate_scheme_code(raw: str) -> str:
    value = (raw or "").strip()
    if not value or not _SCHEME_CODE_RE.match(value):
        raise ValidationError("invalid_scheme_code")
    return value


def validate_scheme_name(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValidationError("missing_scheme_name")
    return value


def validate_nav(raw: str) -> Decimal:
    value = (raw or "").strip()
    if not value:
        raise ValidationError("missing_nav")
    try:
        nav = Decimal(value)
    except InvalidOperation:
        raise ValidationError("invalid_nav_format") from None
    if nav <= 0:
        raise ValidationError("nav_not_positive")
    return nav


def validate_nav_date(raw: str) -> str:
    """Returns an ISO-8601 (YYYY-MM-DD) date string."""
    value = (raw or "").strip()
    if not value:
        raise ValidationError("missing_nav_date")
    try:
        parsed = datetime.strptime(value, _NAV_DATE_FORMAT)
    except ValueError:
        raise ValidationError("invalid_nav_date") from None
    return parsed.strftime("%Y-%m-%d")


def normalize_isin(raw: str) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (normalized_isin_or_None, warning_or_None).

    A legitimately absent ISIN (AMFI's "-", or blank/N.A. variants)
    normalizes to None with no warning -- this is the expected, common
    case and must never cause a row rejection on its own.

    A *present but malformed* ISIN also normalizes to None (never
    fabricated or guessed into shape), but carries an explicit warning
    so the anomaly is visible rather than silently discarded.
    """
    value = (raw or "").strip()
    if value.lower() in _ISIN_ABSENT_TOKENS:
        return None, None
    if _ISIN_SHAPE_RE.match(value.upper()):
        return value.upper(), None
    return None, f"isin_format_invalid: '{value}' treated as missing"
