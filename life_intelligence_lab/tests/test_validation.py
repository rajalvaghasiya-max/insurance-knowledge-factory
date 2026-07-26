from decimal import Decimal

import pytest

from life_intelligence_lab.validation import (
    ValidationError,
    normalize_isin,
    validate_nav,
    validate_nav_date,
    validate_scheme_code,
    validate_scheme_name,
)


def test_validate_scheme_code_valid():
    assert validate_scheme_code("118551") == "118551"


def test_validate_scheme_code_invalid():
    with pytest.raises(ValidationError, match="invalid_scheme_code"):
        validate_scheme_code("ABCDE")


def test_validate_scheme_code_empty():
    with pytest.raises(ValidationError, match="invalid_scheme_code"):
        validate_scheme_code("")


def test_validate_nav_valid_preserves_precision():
    nav = validate_nav("1234.5678")
    assert nav == Decimal("1234.5678")
    assert str(nav) == "1234.5678"


def test_validate_nav_zero_rejected():
    with pytest.raises(ValidationError, match="nav_not_positive"):
        validate_nav("0.0000")


def test_validate_nav_negative_rejected():
    with pytest.raises(ValidationError, match="nav_not_positive"):
        validate_nav("-5.0000")


def test_validate_nav_non_numeric_rejected():
    with pytest.raises(ValidationError, match="invalid_nav_format"):
        validate_nav("N.A.")


def test_validate_nav_date_valid():
    assert validate_nav_date("25-Jul-2026") == "2026-07-25"


def test_validate_nav_date_invalid_format():
    with pytest.raises(ValidationError, match="invalid_nav_date"):
        validate_nav_date("2026/07/25")


def test_validate_scheme_name_valid():
    assert validate_scheme_name("  Some Fund  ") == "Some Fund"


def test_validate_scheme_name_empty_rejected():
    with pytest.raises(ValidationError, match="missing_scheme_name"):
        validate_scheme_name("")


def test_normalize_isin_dash_is_absent_no_warning():
    isin, warning = normalize_isin("-")
    assert isin is None
    assert warning is None


def test_normalize_isin_empty_is_absent_no_warning():
    isin, warning = normalize_isin("")
    assert isin is None
    assert warning is None


def test_normalize_isin_valid_shape():
    isin, warning = normalize_isin("inf209k01un8")
    assert isin == "INF209K01UN8"
    assert warning is None


def test_normalize_isin_malformed_becomes_none_with_warning():
    isin, warning = normalize_isin("NOTANISINVALUE")
    assert isin is None
    assert warning is not None
    assert "isin_format_invalid" in warning
