from life_intelligence_lab.calculators.contracts import RESULT_STATUS_UNSUPPORTED_CALCULATOR
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _base_request(**overrides):
    request = {
        "request_id": "req_reg",
        "calculator_id": "FV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": "100000", "periodic_rate": "8", "periods": "10"},
        "input_units": {"periodic_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": "idem_reg",
    }
    request.update(overrides)
    return request


# --- 15. Unknown calculator --------------------------------------------------------

def test_unknown_calculator_id_fails_closed():
    request = _base_request(calculator_id="TOTALLY_MADE_UP_CALCULATOR")
    result, trace = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_UNSUPPORTED_CALCULATOR
    assert result.reason == "unknown_calculator_id"
    assert trace is None
    assert result.output_values is None


# --- 16. Unsupported calculator version ---------------------------------------------

def test_unsupported_calculator_version_fails_closed():
    request = _base_request(calculator_version=999)
    result, trace = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_UNSUPPORTED_CALCULATOR
    assert result.reason == "unknown_calculator_version"
    assert trace is None


# --- 17. Retired calculator rejected for new execution --------------------------------

def test_retired_calculator_rejected():
    request = _base_request(calculator_version=0)  # v0 is deliberately retired in the registry
    result, trace = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_UNSUPPORTED_CALCULATOR
    assert result.reason == "calculator_retired"
    assert trace is None
    assert result.output_values is None
    assert any("v1" in w for w in result.warnings)  # points caller to the active successor


def test_active_version_still_works_alongside_retired_version():
    request_v1 = _base_request(calculator_version=1)
    result_v1, trace_v1 = execute_calculation_request(request_v1)
    assert result_v1.status == "SUCCESS"
    assert trace_v1 is not None
