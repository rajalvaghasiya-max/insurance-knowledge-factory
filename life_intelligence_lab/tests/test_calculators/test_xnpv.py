from life_intelligence_lab.calculators.contracts import (
    RESULT_STATUS_FAILED_CLOSED,
    RESULT_STATUS_INVALID_INPUT,
    RESULT_STATUS_SUCCESS,
)
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _cf(date, amount, source_type="premium"):
    return {"date": date, "amount": amount, "currency": "INR", "source_type": source_type}


def _xnpv_request(rate, cash_flows, rate_unit="decimal", request_id="req_xnpv"):
    return {
        "request_id": request_id,
        "calculator_id": "XNPV_DATED",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"rate": rate, "day_count_convention": "ACT_365", "duplicate_date_policy": "REJECT_DUPLICATES"},
        "input_units": {"rate": rate_unit},
        "currency": None,
        "idempotency_key": f"idem_{request_id}",
        "cash_flows": cash_flows,
    }


_KNOWN_ANSWER_FLOWS = [
    _cf("2020-01-01", "-10000"),
    _cf("2020-03-01", "5750"),
    _cf("2020-10-30", "4250"),
    _cf("2021-02-15", "3250"),
]


def test_xnpv_at_xirr_rate_is_near_zero():
    result, trace = execute_calculation_request(_xnpv_request("0.6342972615260243", _KNOWN_ANSWER_FLOWS))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["xnpv"] == "0.00"


def test_xnpv_at_zero_rate_equals_sum_of_flows():
    result, _ = execute_calculation_request(_xnpv_request("0", _KNOWN_ANSWER_FLOWS))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["xnpv"] == "3250.00"  # -10000+5750+4250+3250


# --- 12. XNPV rate <= -1 ---------------------------------------------------------

def test_xnpv_rate_exactly_negative_one_fails_closed():
    result, trace = execute_calculation_request(_xnpv_request("-1", _KNOWN_ANSWER_FLOWS))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert "xnpv_rate_out_of_domain" in result.reason
    assert trace is None
    assert result.output_values is None


def test_xnpv_rate_below_negative_one_fails_closed():
    result, _ = execute_calculation_request(_xnpv_request("-1.5", _KNOWN_ANSWER_FLOWS))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert "xnpv_rate_out_of_domain" in result.reason


def test_xnpv_ambiguous_rate_unit_rejected():
    req = _xnpv_request("8", _KNOWN_ANSWER_FLOWS)
    req["input_units"] = {}
    result, _ = execute_calculation_request(req)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "ambiguous_rate_unit" in result.reason


def test_xnpv_empty_cash_flows_rejected():
    result, _ = execute_calculation_request(_xnpv_request("0.1", []))
    assert result.status == RESULT_STATUS_INVALID_INPUT


def test_xnpv_has_no_root_status_concept():
    result, _ = execute_calculation_request(_xnpv_request("0.1", _KNOWN_ANSWER_FLOWS))
    assert result.root_status is None  # XNPV evaluates, it does not solve for a root
