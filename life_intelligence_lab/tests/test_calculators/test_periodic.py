from life_intelligence_lab.calculators.contracts import (
    RESULT_STATUS_FAILED_CLOSED,
    RESULT_STATUS_INVALID_INPUT,
    RESULT_STATUS_SUCCESS,
    ROOT_STATUS_INVALID_CASH_FLOWS,
    ROOT_STATUS_SINGLE_ROOT,
)
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _irr_request(flows, request_id="req_irr_periodic"):
    return {
        "request_id": request_id, "calculator_id": "IRR_PERIODIC", "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"cash_flows": flows}, "input_units": {}, "currency": None,
        "idempotency_key": f"idem_{request_id}",
    }


def _npv_request(rate, flows, rate_unit="decimal", request_id="req_npv_periodic"):
    return {
        "request_id": request_id, "calculator_id": "NPV_PERIODIC", "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"rate": rate, "cash_flows": flows}, "input_units": {"rate": rate_unit},
        "currency": "INR", "idempotency_key": f"idem_{request_id}",
    }


# --- Periodic IRR known-answer vector (section 17) ---------------------------

def test_periodic_irr_known_answer_vector():
    flows = ["-250000", "100000", "150000", "200000", "250000", "300000"]
    result, trace = execute_calculation_request(_irr_request(flows))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.root_status == ROOT_STATUS_SINGLE_ROOT
    assert result.output_values["rate"] == "0.567230"
    assert trace.steps[-1].unrounded_value.startswith("0.5672303344358")


def test_periodic_npv_at_irr_rate_is_near_zero():
    flows = ["-250000", "100000", "150000", "200000", "250000", "300000"]
    irr_result, _ = execute_calculation_request(_irr_request(flows))
    npv_result, _ = execute_calculation_request(
        _npv_request(irr_result.output_values["rate"], flows)
    )
    assert npv_result.status == RESULT_STATUS_SUCCESS
    assert abs(float(npv_result.output_values["npv"])) < 1.0  # near zero, within rounding of a rounded rate


def test_periodic_npv_at_zero_rate_equals_sum():
    flows = ["-100", "50", "60"]
    result, _ = execute_calculation_request(_npv_request("0", flows))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["npv"] == "10.00"


def test_periodic_irr_all_positive_fails_closed():
    result, _ = execute_calculation_request(_irr_request(["100", "200", "300"]))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert result.root_status == ROOT_STATUS_INVALID_CASH_FLOWS


def test_periodic_irr_all_negative_fails_closed():
    result, _ = execute_calculation_request(_irr_request(["-100", "-200"]))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert result.root_status == ROOT_STATUS_INVALID_CASH_FLOWS


def test_periodic_irr_single_flow_fails_closed():
    result, _ = execute_calculation_request(_irr_request(["-100"]))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert result.root_status == ROOT_STATUS_INVALID_CASH_FLOWS


def test_periodic_irr_empty_list_rejected():
    result, _ = execute_calculation_request(_irr_request([]))
    assert result.status == RESULT_STATUS_INVALID_INPUT


def test_periodic_npv_rate_le_negative_one_fails_closed():
    result, _ = execute_calculation_request(_npv_request("-1", ["-100", "50", "60"]))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert "npv_periodic_rate_out_of_domain" in result.reason


def test_periodic_calculators_have_no_day_count_or_duplicate_policy_fields():
    from life_intelligence_lab.calculators import registry
    irr_def = registry.get("IRR_PERIODIC", 1)
    npv_def = registry.get("NPV_PERIODIC", 1)
    assert irr_def.supported_day_count_conventions == []
    assert npv_def.supported_day_count_conventions == []
    assert "date" not in irr_def.required_input_schema
    assert "date" not in npv_def.required_input_schema


def test_periodic_terminology_distinct_from_dated_terminology():
    # Section 11's explicit instruction: periodic must not be confused
    # with dated XIRR. Verify the calculator ids and formula ids never
    # cross-reference each other's terminology.
    from life_intelligence_lab.calculators import registry
    irr_periodic_def = registry.get("IRR_PERIODIC", 1)
    xirr_def = registry.get("XIRR_DATED", 1)
    assert "XIRR" not in irr_periodic_def.formula_id
    assert "PERIODIC" not in xirr_def.formula_id
    assert irr_periodic_def.formula_description != xirr_def.formula_description
