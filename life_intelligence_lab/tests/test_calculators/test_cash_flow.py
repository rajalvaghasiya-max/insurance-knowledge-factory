from life_intelligence_lab.calculators.cash_flow import normalize_cash_flow_list
from life_intelligence_lab.calculators.normalization import NormalizationError


def _cf(date, amount, currency="INR", source_type="premium"):
    return {"date": date, "amount": amount, "currency": currency, "source_type": source_type}


def test_normalize_simple_list():
    normalized, ops, currency = normalize_cash_flow_list(
        [_cf("2020-01-01", "-10000"), _cf("2021-01-01", "12000")], "REJECT_DUPLICATES"
    )
    assert len(normalized) == 2
    assert currency == "INR"
    assert ops == []
    assert normalized[0].amount == "-10000"


def test_id_is_deterministic_not_random():
    a, _, _ = normalize_cash_flow_list([_cf("2020-01-01", "-100"), _cf("2021-01-01", "200")], "REJECT_DUPLICATES")
    b, _, _ = normalize_cash_flow_list([_cf("2020-01-01", "-100"), _cf("2021-01-01", "200")], "REJECT_DUPLICATES")
    assert a[0].cash_flow_id == b[0].cash_flow_id


# --- 5. Duplicate dates with REJECT_DUPLICATES ------------------------------

def test_duplicate_dates_rejected():
    raw = [_cf("2020-01-01", "-100"), _cf("2020-01-01", "-50"), _cf("2021-01-01", "200")]
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False, "expected NormalizationError"
    except NormalizationError as exc:
        assert "duplicate_date_rejected" in str(exc)


# --- 6. Duplicate dates with NET_SAME_DATE ----------------------------------

def test_duplicate_dates_netted_with_provenance():
    raw = [_cf("2020-01-01", "-100"), _cf("2020-01-01", "-50"), _cf("2021-01-01", "200")]
    normalized, ops, _ = normalize_cash_flow_list(raw, "NET_SAME_DATE")
    net_flow = next(cf for cf in normalized if cf.date == "2020-01-01")
    assert net_flow.amount == "-150"
    assert len(ops) == 1
    assert ops[0].net_amount == "-150"
    assert len(ops[0].original_cash_flow_ids) == 2


# --- 7. Same-date flows netting to zero -------------------------------------

def test_same_date_net_to_zero_is_retained_explicitly():
    raw = [
        _cf("2020-01-01", "-10000"),
        _cf("2020-06-01", "500"),
        _cf("2020-06-01", "-500"),
        _cf("2021-01-01", "12000"),
    ]
    normalized, ops, _ = normalize_cash_flow_list(raw, "NET_SAME_DATE")
    zero_flow = next(cf for cf in normalized if cf.date == "2020-06-01")
    assert zero_flow.amount == "0"
    assert len(normalized) == 3  # not dropped
    assert "retained explicitly" in ops[0].note


# --- 8. Invalid date ----------------------------------------------------------

def test_invalid_date_rejected():
    raw = [_cf("2020-13-45", "-100"), _cf("2021-01-01", "200")]
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "invalid_date_format" in str(exc)


def test_non_iso_date_format_rejected():
    raw = [_cf("01-Jan-2020", "-100"), _cf("2021-01-01", "200")]
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "invalid_date_format" in str(exc)


# --- 9. Mixed currencies -----------------------------------------------------

def test_mixed_currencies_rejected():
    raw = [_cf("2020-01-01", "-100", currency="INR"), _cf("2021-01-01", "200", currency="USD")]
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "mixed_currencies" in str(exc)


# --- 10/11. NaN / Infinity amount ---------------------------------------------

def test_nan_amount_rejected():
    raw = [_cf("2020-01-01", "NaN"), _cf("2021-01-01", "200")]
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "non_finite_value" in str(exc)


def test_infinity_amount_rejected():
    raw = [_cf("2020-01-01", "Infinity"), _cf("2021-01-01", "200")]
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "non_finite_value" in str(exc)


# --- 4. Empty list -----------------------------------------------------------

def test_empty_list_rejected():
    try:
        normalize_cash_flow_list([], "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "empty_cash_flow_list" in str(exc)


# --- 14. Unsupported duplicate policy -----------------------------------------

def test_unsupported_duplicate_policy_rejected():
    raw = [_cf("2020-01-01", "-100"), _cf("2021-01-01", "200")]
    try:
        normalize_cash_flow_list(raw, "IGNORE_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "unsupported_duplicate_date_policy" in str(exc)


# --- 18. Cash-flow ordering permutations --------------------------------------

def test_ordering_permutation_does_not_affect_canonical_output():
    raw_a = [_cf("2020-01-01", "-100"), _cf("2020-06-01", "50"), _cf("2021-01-01", "100")]
    raw_b = [_cf("2021-01-01", "100"), _cf("2020-01-01", "-100"), _cf("2020-06-01", "50")]
    normalized_a, _, _ = normalize_cash_flow_list(raw_a, "REJECT_DUPLICATES")
    normalized_b, _, _ = normalize_cash_flow_list(raw_b, "REJECT_DUPLICATES")
    assert [cf.date for cf in normalized_a] == [cf.date for cf in normalized_b]
    assert [cf.amount for cf in normalized_a] == [cf.amount for cf in normalized_b]


# --- 27/28. Very close dates and long-duration dates --------------------------

def test_very_close_dates():
    raw = [_cf("2020-01-01", "-100"), _cf("2020-01-02", "100.5")]
    normalized, _, _ = normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
    assert normalized[0].date == "2020-01-01"
    assert normalized[1].date == "2020-01-02"


def test_long_duration_dates():
    raw = [_cf("1990-01-01", "-1000"), _cf("2050-01-01", "50000")]
    normalized, _, _ = normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
    assert normalized[0].date == "1990-01-01"
    assert normalized[1].date == "2050-01-01"


# --- 29. Decimal amount precision ----------------------------------------------

def test_decimal_amount_precision_preserved():
    raw = [_cf("2020-01-01", "-10000.123456"), _cf("2021-01-01", "12000.654321")]
    normalized, _, _ = normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
    assert normalized[0].amount == "-10000.123456"
    assert normalized[1].amount == "12000.654321"


# --- 30. Duplicate IDs with different contents (never happens by construction) --

def test_ids_differ_for_different_content_at_same_sequence():
    raw_1 = [_cf("2020-01-01", "-100"), _cf("2021-01-01", "200")]
    raw_2 = [_cf("2020-01-01", "-999"), _cf("2021-01-01", "200")]
    normalized_1, _, _ = normalize_cash_flow_list(raw_1, "REJECT_DUPLICATES")
    normalized_2, _, _ = normalize_cash_flow_list(raw_2, "REJECT_DUPLICATES")
    # Same sequence position, different amount -> different derived id.
    assert normalized_1[0].cash_flow_id != normalized_2[0].cash_flow_id


def test_missing_required_cash_flow_field_rejected():
    raw = [{"date": "2020-01-01", "currency": "INR", "source_type": "premium"}]  # no amount
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "missing_required_input" in str(exc)


def test_float_amount_type_rejected():
    raw = [_cf("2020-01-01", -100.0), _cf("2021-01-01", "200")]
    try:
        normalize_cash_flow_list(raw, "REJECT_DUPLICATES")
        assert False
    except NormalizationError as exc:
        assert "malformed_decimal_value" in str(exc)
