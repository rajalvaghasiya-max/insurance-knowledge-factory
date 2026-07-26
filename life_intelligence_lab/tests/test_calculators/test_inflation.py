from life_intelligence_lab.calculators.contracts import RESULT_STATUS_SUCCESS
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _inflation_request(method=None, calculator_id="INFLATION_ADJUSTED_FV"):
    request = {
        "request_id": f"req_infl_{calculator_id}_{method}",
        "calculator_id": calculator_id,
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {
            "present_value": "100000",
            "nominal_rate": "8",
            "inflation_rate": "6",
            "periods": "10",
        },
        "input_units": {"nominal_rate": "percentage", "inflation_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": f"idem_infl_{calculator_id}_{method}",
    }
    if method is not None:
        request["method"] = method
    return request


# --- 5. Exact inflation-adjusted vector -----------------------------------------

def test_inflation_exact_deflate_nominal_method():
    result, trace = execute_calculation_request(_inflation_request(method="deflate_nominal"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["real_future_value"] == "120553.24"


def test_inflation_exact_real_rate_method():
    result, trace = execute_calculation_request(_inflation_request(method="exact_real_rate"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["real_future_value"] == "120553.24"


def test_inflation_method_is_required_no_default():
    from life_intelligence_lab.calculators.contracts import RESULT_STATUS_INVALID_INPUT
    result, _ = execute_calculation_request(_inflation_request(method=None))
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "missing_or_unsupported_method" in result.reason


# --- 6. Approximate inflation-adjusted vector -----------------------------------

def test_inflation_approximate_vector():
    result, trace = execute_calculation_request(_inflation_request(calculator_id="INFLATION_ADJUSTED_FV_APPROX"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["real_future_value"] == "121899.44"


def test_inflation_approximate_result_carries_explicit_inexactness_warning():
    result, _ = execute_calculation_request(_inflation_request(calculator_id="INFLATION_ADJUSTED_FV_APPROX"))
    combined = " ".join(result.warnings).lower()
    assert "not the exact fisher relationship" in combined
    assert "approximate" in combined


# --- 7. Exact and approximate results differ ------------------------------------

def test_exact_and_approximate_results_differ():
    exact_a, _ = execute_calculation_request(_inflation_request(method="deflate_nominal"))
    exact_b, _ = execute_calculation_request(_inflation_request(method="exact_real_rate"))
    approx, _ = execute_calculation_request(_inflation_request(calculator_id="INFLATION_ADJUSTED_FV_APPROX"))

    # The two EXACT methods must agree with each other.
    assert exact_a.output_values["real_future_value"] == exact_b.output_values["real_future_value"]
    # The approximate method must NOT match the exact methods.
    assert approx.output_values["real_future_value"] != exact_a.output_values["real_future_value"]


def test_approximate_is_a_separate_calculator_id_not_a_hidden_mode():
    # The approximate method is never reachable through the exact
    # calculator's own method selection.
    from life_intelligence_lab.calculators import registry
    exact_def = registry.get("INFLATION_ADJUSTED_FV", 1)
    assert "approximate" not in [m.lower() for m in exact_def.supported_methods]
    assert set(exact_def.supported_methods) == {"deflate_nominal", "exact_real_rate"}
