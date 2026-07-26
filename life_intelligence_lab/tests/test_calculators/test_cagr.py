from life_intelligence_lab.calculators.contracts import RESULT_STATUS_FAILED_CLOSED, RESULT_STATUS_SUCCESS
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _cagr_request(beginning, ending, periods, allow_negative=None):
    input_values = {"beginning_value": beginning, "ending_value": ending, "periods": periods}
    if allow_negative is not None:
        input_values["allow_negative_values"] = allow_negative
    return {
        "request_id": f"req_cagr_{beginning}_{ending}_{periods}",
        "calculator_id": "CAGR",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": input_values,
        "input_units": {},
        "currency": None,
        "idempotency_key": f"idem_cagr_{beginning}_{ending}_{periods}",
    }


# --- 4. CAGR known-answer vector -----------------------------------------------

def test_cagr_known_answer_vector():
    result, trace = execute_calculation_request(_cagr_request("100000", "200000", "6"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["cagr_percentage"] == "12.2462"
    assert result.output_values["cagr"] == "0.122462"


# --- 12. CAGR beginning value zero rejected -------------------------------------

def test_cagr_beginning_value_zero_fails_closed():
    result, trace = execute_calculation_request(_cagr_request("0", "200000", "6"))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert "cagr_beginning_value_zero" in result.reason
    assert trace is None
    assert result.output_values is None  # no plausible-looking number


# --- 13. CAGR negative values rejected -------------------------------------------

def test_cagr_negative_values_rejected_by_default():
    result, _ = execute_calculation_request(_cagr_request("-100000", "200000", "6"))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert "cagr_negative_value_not_supported" in result.reason


def test_cagr_negative_values_allowed_with_explicit_flag():
    result, _ = execute_calculation_request(_cagr_request("-100000", "-50000", "6", allow_negative="true"))
    assert result.status == RESULT_STATUS_SUCCESS


def test_cagr_periods_zero_rejected():
    result, _ = execute_calculation_request(_cagr_request("100000", "200000", "0"))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert "cagr_periods_must_be_positive" in result.reason


def test_cagr_negative_periods_rejected_generically_before_reaching_formula():
    # Negative periods are rejected at the generic normalization layer
    # (INVALID_INPUT), never reaching CAGR's own domain check.
    from life_intelligence_lab.calculators.contracts import RESULT_STATUS_INVALID_INPUT
    result, _ = execute_calculation_request(_cagr_request("100000", "200000", "-3"))
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "negative_period_count" in result.reason
