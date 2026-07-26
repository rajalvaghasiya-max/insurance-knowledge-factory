from life_intelligence_lab.calculators.contracts import RESULT_STATUS_SUCCESS
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _fv_request(present_value, rate, periods, rate_unit="percentage"):
    return {
        "request_id": f"req_fv_{present_value}_{rate}_{periods}",
        "calculator_id": "FV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": present_value, "periodic_rate": rate, "periods": periods},
        "input_units": {"periodic_rate": rate_unit},
        "currency": "INR",
        "idempotency_key": f"idem_fv_{present_value}_{rate}_{periods}",
    }


# --- 1. Future value known-answer vector ------------------------------------

def test_fv_known_answer_vector():
    result, trace = execute_calculation_request(_fv_request("100000", "8", "10"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["future_value"] == "215892.50"


# --- 2. Future value 15-year regression vector (LIFE-003) -------------------

def test_fv_15_year_regression_vector_matches_life_003():
    """
    This is the vector explicitly required to prevent recurrence of the
    numerical inconsistency identified in LIFE-003 -- LIFE-003's own
    prose draft momentarily left a placeholder/incorrect figure for this
    exact case before being corrected. Locking it in as a known-answer
    test makes that class of error mechanically impossible to reintroduce.
    """
    result, trace = execute_calculation_request(_fv_request("100000", "8", "15"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["future_value"] == "317216.91"


def test_fv_zero_rate():
    result, _ = execute_calculation_request(_fv_request("100000", "0", "10"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["future_value"] == "100000.00"


def test_fv_zero_periods_is_valid():
    result, _ = execute_calculation_request(_fv_request("100000", "8", "0"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["future_value"] == "100000.00"


def test_fv_negative_rate_is_allowed():
    # A negative periodic rate (e.g. a declining-value scenario) is a
    # well-formed, well-typed decimal rate -- not something normalization
    # should reject. FV/PV impose no domain restriction on rate sign.
    result, _ = execute_calculation_request(_fv_request("100000", "-5", "10"))
    assert result.status == RESULT_STATUS_SUCCESS
    # 100000 * (0.95)^10
    from decimal import Decimal
    expected = (Decimal("100000") * (Decimal("0.95") ** 10)).quantize(Decimal("0.01"))
    assert result.output_values["future_value"] == str(expected)


def test_fv_output_carries_projection_not_guarantee_warning():
    result, _ = execute_calculation_request(_fv_request("100000", "8", "10"))
    assert any("not a guarantee" in w.lower() or "not a guaranteed" in w.lower() for w in result.warnings)
    assert any("projection" in lim.lower() for lim in result.limitations)
