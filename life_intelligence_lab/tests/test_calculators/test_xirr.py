from life_intelligence_lab.calculators.contracts import (
    RESULT_STATUS_FAILED_CLOSED,
    RESULT_STATUS_INVALID_INPUT,
    RESULT_STATUS_SUCCESS,
    ROOT_STATUS_DEPENDENCY_FAILURE,
    ROOT_STATUS_INVALID_CASH_FLOWS,
    ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE,
    ROOT_STATUS_SINGLE_ROOT,
)
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _xirr_request(cash_flows, duplicate_date_policy="REJECT_DUPLICATES", request_id="req_xirr"):
    return {
        "request_id": request_id,
        "calculator_id": "XIRR_DATED",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"day_count_convention": "ACT_365", "duplicate_date_policy": duplicate_date_policy},
        "input_units": {},
        "currency": None,
        "idempotency_key": f"idem_{request_id}",
        "cash_flows": cash_flows,
    }


def _cf(date, amount, source_type="premium"):
    return {"date": date, "amount": amount, "currency": "INR", "source_type": source_type}


# --- XIRR known-answer vector (section 17) ------------------------------------

def test_xirr_known_answer_vector():
    cash_flows = [
        _cf("2020-01-01", "-10000"),
        _cf("2020-03-01", "5750"),
        _cf("2020-10-30", "4250"),
        _cf("2021-02-15", "3250"),
    ]
    result, trace = execute_calculation_request(_xirr_request(cash_flows))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.root_status == ROOT_STATUS_SINGLE_ROOT
    assert result.output_values["rate"] == "0.634297"
    assert result.output_values["rate_percentage"] == "63.4297"
    # Full unrounded precision preserved in the trace.
    assert trace.output_before_rounding["rate"].startswith("0.6342972615260")


def test_xirr_xnpv_consistency_check_recorded_and_passes():
    cash_flows = [
        _cf("2020-01-01", "-10000"),
        _cf("2020-03-01", "5750"),
        _cf("2020-10-30", "4250"),
        _cf("2021-02-15", "3250"),
    ]
    result, trace = execute_calculation_request(_xirr_request(cash_flows))
    check = trace.dated_cash_flow_context["xnpv_consistency_check"]
    assert check["within_tolerance"] is True
    assert abs(float(check["xnpv_at_root"])) < 0.01


# --- 1. All positive flows ------------------------------------------------------

def test_all_positive_flows_fail_closed():
    result, trace = execute_calculation_request(
        _xirr_request([_cf("2020-01-01", "100"), _cf("2020-06-01", "200")])
    )
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert result.root_status == ROOT_STATUS_INVALID_CASH_FLOWS
    assert trace is None
    assert result.output_values is None


# --- 2. All negative flows -------------------------------------------------------

def test_all_negative_flows_fail_closed():
    result, _ = execute_calculation_request(
        _xirr_request([_cf("2020-01-01", "-100"), _cf("2020-06-01", "-200")])
    )
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert result.root_status == ROOT_STATUS_INVALID_CASH_FLOWS


# --- 3. One flow only -------------------------------------------------------------

def test_single_flow_fails_closed():
    result, _ = execute_calculation_request(_xirr_request([_cf("2020-01-01", "-100")]))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert result.root_status == ROOT_STATUS_INVALID_CASH_FLOWS


# --- 4. Empty list -----------------------------------------------------------------

def test_empty_cash_flow_list_is_invalid_input():
    result, _ = execute_calculation_request(_xirr_request([]))
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "empty_cash_flow_list" in result.reason


# --- 13. Unsupported day-count convention -----------------------------------------

def test_unsupported_day_count_convention():
    req = _xirr_request([_cf("2020-01-01", "-100"), _cf("2021-01-01", "200")])
    req["input_values"]["day_count_convention"] = "THIRTY_360"
    result, _ = execute_calculation_request(req)
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "day_count_convention" in result.reason


# --- 15. Multiple sign changes -> MULTIPLE_ROOTS_POSSIBLE ---------------------------

def test_multiple_sign_changes_produces_candidate_with_warning():
    cash_flows = [
        _cf("2020-01-01", "-100"),
        _cf("2020-06-01", "1000"),
        _cf("2020-12-01", "-100"),
        _cf("2021-06-01", "-1000"),
    ]
    result, trace = execute_calculation_request(_xirr_request(cash_flows))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.root_status == ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE
    assert any("MULTIPLE ROOTS POSSIBLE" in w for w in result.warnings)
    assert any("CANDIDATE" in w for w in result.warnings)  # never presented as uniquely correct


# --- 16. No root ---------------------------------------------------------------------

def test_no_root_found_fails_closed():
    cash_flows = [
        _cf("2020-01-01", "-1000"),
        _cf("2021-01-01", "3000"),
        _cf("2022-01-01", "-2500"),
    ]
    result, trace = execute_calculation_request(_xirr_request(cash_flows))
    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert "xirr_no_root_found" in result.reason
    assert trace is None
    assert result.output_values is None


# --- 26. Zero XIRR ---------------------------------------------------------------------

def test_zero_xirr_is_a_valid_success_not_a_failure():
    cash_flows = [_cf("2020-01-01", "-1000"), _cf("2021-01-01", "1000")]
    result, trace = execute_calculation_request(_xirr_request(cash_flows))
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["rate"] == "0.000000"
    assert result.root_status == ROOT_STATUS_SINGLE_ROOT


# --- 17/25. Dependency failure (simulated, deterministic) ----------------------------

def test_dependency_failure_maps_to_failed_closed_with_root_status():
    import life_intelligence_lab.calculators.runtime as runtime_module
    from life_intelligence_lab.calculators.adapters.pyxirr_adapter import PyXirrAdapter
    from life_intelligence_lab.calculators.formulas import xirr as xirr_formula

    class _CrashingEngine:
        class InvalidPaymentsError(Exception):
            pass

        def xirr(self, *a, **k):
            raise RuntimeError("simulated catastrophic engine failure")

    original = runtime_module._DISPATCH["XIRR_DATED"]

    def crashing_dispatch(normalized, method, context):
        return xirr_formula.compute(
            normalized, method,
            cash_flows=context["cash_flows"], duplicate_date_operations=context["duplicate_date_operations"],
            day_count_convention=context["day_count_convention"], duplicate_date_policy=context["duplicate_date_policy"],
            currency=context["currency"], adapter=PyXirrAdapter(engine=_CrashingEngine()),
        )

    runtime_module._DISPATCH["XIRR_DATED"] = crashing_dispatch
    try:
        result, trace = execute_calculation_request(
            _xirr_request([_cf("2020-01-01", "-10000"), _cf("2021-01-01", "12000")])
        )
    finally:
        runtime_module._DISPATCH["XIRR_DATED"] = original

    assert result.status == RESULT_STATUS_FAILED_CLOSED
    assert result.root_status == ROOT_STATUS_DEPENDENCY_FAILURE
    assert "dependency_failure" in result.reason
    assert trace is None
    assert result.output_values is None


def test_duplicate_dates_rejected_at_runtime_level():
    cash_flows = [_cf("2020-01-01", "-100"), _cf("2020-01-01", "-50"), _cf("2021-01-01", "200")]
    result, _ = execute_calculation_request(_xirr_request(cash_flows, duplicate_date_policy="REJECT_DUPLICATES"))
    assert result.status == RESULT_STATUS_INVALID_INPUT
    assert "duplicate_date_rejected" in result.reason


def test_duplicate_dates_netted_at_runtime_level():
    cash_flows = [_cf("2020-01-01", "-100"), _cf("2020-01-01", "-50"), _cf("2021-01-01", "200")]
    result, trace = execute_calculation_request(_xirr_request(cash_flows, duplicate_date_policy="NET_SAME_DATE"))
    assert result.status == RESULT_STATUS_SUCCESS
    assert len(trace.dated_cash_flow_context["duplicate_date_operations"]) == 1


def test_trace_never_contains_executable_code():
    cash_flows = [_cf("2020-01-01", "-10000"), _cf("2021-01-01", "12000")]
    result, trace = execute_calculation_request(_xirr_request(cash_flows))
    for step in trace.steps:
        assert "eval(" not in step.expression
        assert "exec(" not in step.expression
        assert "__import__" not in step.expression
