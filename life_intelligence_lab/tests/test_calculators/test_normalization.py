from life_intelligence_lab.calculators.contracts import RESULT_STATUS_INVALID_INPUT
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _base_request(**overrides):
    request = {
        "request_id": "req_norm",
        "calculator_id": "FV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": "100000", "periodic_rate": "8", "periods": "10"},
        "input_units": {"periodic_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": "idem_norm",
    }
    request.update(overrides)
    return request


# --- 11. Negative periods rejected -----------------------------------------------

def test_negative_periods_rejected():
    request = _base_request(input_values={"present_value": "100000", "periodic_rate": "8", "periods": "-5"})
    result, trace = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "negative_period_count" in result.reason
    assert trace is None
    assert result.output_values is None


# --- 14. Missing required input --------------------------------------------------

def test_missing_required_input():
    request = _base_request(input_values={"present_value": "100000", "periodic_rate": "8"})
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "missing_required_input:periods" in result.reason


# --- 18. Ambiguous percentage input -----------------------------------------------

def test_ambiguous_rate_unit_rejected():
    request = _base_request(input_units={})  # no unit given for periodic_rate
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "ambiguous_rate_unit" in result.reason


def test_percentage_and_decimal_units_are_not_guessed_from_magnitude():
    # "8" as decimal means 800% growth per period; "8" as percentage means
    # 8%. The runtime must use exactly the unit given, never infer one
    # from the number's magnitude.
    request_decimal = _base_request(input_units={"periodic_rate": "decimal"})
    result_decimal, _ = execute_calculation_request(request_decimal)
    request_percentage = _base_request(input_units={"periodic_rate": "percentage"})
    result_percentage, _ = execute_calculation_request(request_percentage)
    assert result_decimal.output_values["future_value"] != result_percentage.output_values["future_value"]


# --- 19. Invalid unit ------------------------------------------------------------

def test_invalid_unit_rejected():
    request = _base_request(input_units={"periodic_rate": "basis_points"})
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "invalid_unit" in result.reason


# --- 20. NaN or infinity rejected --------------------------------------------------

def test_nan_rejected():
    request = _base_request(input_values={"present_value": "NaN", "periodic_rate": "8", "periods": "10"})
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "non_finite_value" in result.reason


def test_infinity_rejected():
    request = _base_request(input_values={"present_value": "Infinity", "periodic_rate": "8", "periods": "10"})
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "non_finite_value" in result.reason


def test_negative_infinity_rejected():
    request = _base_request(input_values={"present_value": "100000", "periodic_rate": "-Infinity", "periods": "10"})
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "non_finite_value" in result.reason


# Additional coverage: float type and malformed decimal rejection

def test_float_type_input_rejected():
    request = _base_request(input_values={"present_value": 100000.0, "periodic_rate": "8", "periods": "10"})
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "malformed_decimal_value" in result.reason


def test_malformed_decimal_string_rejected():
    request = _base_request(input_values={"present_value": "not-a-number", "periodic_rate": "8", "periods": "10"})
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "malformed_decimal_value" in result.reason


def test_unsupported_currency_rejected():
    request = _base_request(currency="ZZZ")
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "unsupported_currency_format" in result.reason


def test_missing_currency_rejected_when_required():
    request = _base_request(currency=None)
    result, _ = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "missing_required_input:currency" in result.reason
