import dataclasses
import json

from life_intelligence_lab.calculators import canonical, serialization
from life_intelligence_lab.calculators.contracts import (
    CALCULATION_RESULT_FIELD_ORDER,
    CALCULATION_TRACE_FIELD_ORDER,
    RESULT_STATUS_FAILED_CLOSED,
)
from life_intelligence_lab.calculators.runtime import execute_calculation_request
from life_intelligence_lab.calculators.validation import validate_result


def _cf(date, amount, source_type="premium"):
    return {"date": date, "amount": amount, "currency": "INR", "source_type": source_type}


def _xirr_request(request_id="req_det"):
    return {
        "request_id": request_id, "calculator_id": "XIRR_DATED", "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"day_count_convention": "ACT_365", "duplicate_date_policy": "REJECT_DUPLICATES"},
        "input_units": {}, "currency": None, "idempotency_key": f"idem_{request_id}",
        "cash_flows": [
            _cf("2020-01-01", "-10000"), _cf("2020-03-01", "5750"),
            _cf("2020-10-30", "4250"), _cf("2021-02-15", "3250"),
        ],
    }


def _xnpv_request(request_id="req_det_xnpv"):
    return {
        "request_id": request_id, "calculator_id": "XNPV_DATED", "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"rate": "0.5", "day_count_convention": "ACT_365", "duplicate_date_policy": "REJECT_DUPLICATES"},
        "input_units": {"rate": "decimal"}, "currency": None, "idempotency_key": f"idem_{request_id}",
        "cash_flows": [_cf("2020-01-01", "-10000"), _cf("2021-01-01", "12000")],
    }


# --- Deterministic hashes (section 19) ------------------------------------------

def test_xirr_repeated_execution_byte_identical():
    result_a, trace_a = execute_calculation_request(_xirr_request())
    result_b, trace_b = execute_calculation_request(_xirr_request())
    assert result_a.deterministic_input_hash == result_b.deterministic_input_hash
    assert result_a.deterministic_output_hash == result_b.deterministic_output_hash
    assert result_a.result_id == result_b.result_id
    assert trace_a.trace_id == trace_b.trace_id
    assert json.dumps(serialization.trace_to_dict(trace_a)) == json.dumps(serialization.trace_to_dict(trace_b))


def test_different_cash_flow_lists_produce_different_input_hash():
    result_a, _ = execute_calculation_request(_xirr_request())
    req_b = _xirr_request()
    req_b["cash_flows"][0]["amount"] = "-9999"  # one cent different
    result_b, _ = execute_calculation_request(req_b)
    assert result_a.deterministic_input_hash != result_b.deterministic_input_hash


def test_cash_flow_order_permutation_does_not_change_hash():
    req_a = _xirr_request(request_id="perm_a")
    req_b = _xirr_request(request_id="perm_a")  # same request_id -> same envelope hash inputs
    req_b["cash_flows"] = list(reversed(req_b["cash_flows"]))
    result_a, _ = execute_calculation_request(req_a)
    result_b, _ = execute_calculation_request(req_b)
    assert result_a.deterministic_input_hash == result_b.deterministic_input_hash


def test_prototype_002_hash_unaffected_by_prototype_003_extension():
    # The exact hash documented in PROTOTYPE_REPORT_002.md before Prototype
    # 003 touched any shared contract -- must still match byte-for-byte.
    req = {
        "request_id": "example_fv_100000_8pct_10y", "calculator_id": "FV_LUMP_SUM", "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": "100000", "periodic_rate": "8", "periods": "10"},
        "input_units": {"periodic_rate": "percentage"}, "currency": "INR",
        "idempotency_key": "example_fv_100000_8pct_10y_v1",
    }
    result, _ = execute_calculation_request(req)
    assert result.deterministic_input_hash == "97331b165263bd86a1991a0c9c4620793655b02f9850d929f0968a666f00bc98"


# --- Trace/result content hashes ------------------------------------------------

def test_trace_content_hash_deterministic():
    _, trace_a = execute_calculation_request(_xirr_request())
    _, trace_b = execute_calculation_request(_xirr_request())
    hash_a = canonical.hash_trace_content(serialization.trace_to_dict(trace_a), CALCULATION_TRACE_FIELD_ORDER)
    hash_b = canonical.hash_trace_content(serialization.trace_to_dict(trace_b), CALCULATION_TRACE_FIELD_ORDER)
    assert hash_a == hash_b


def test_result_content_hash_deterministic():
    result_a, _ = execute_calculation_request(_xirr_request())
    result_b, _ = execute_calculation_request(_xirr_request())
    hash_a = canonical.hash_result_content(serialization.result_to_dict(result_a), CALCULATION_RESULT_FIELD_ORDER)
    hash_b = canonical.hash_result_content(serialization.result_to_dict(result_b), CALCULATION_RESULT_FIELD_ORDER)
    assert hash_a == hash_b


def test_failed_closed_replay_is_also_deterministic():
    result_a, trace_a = execute_calculation_request(_xirr_request())  # baseline success case first (unused)
    req = _xirr_request(request_id="req_failed_det")
    req["cash_flows"] = [_cf("2020-01-01", "100"), _cf("2021-01-01", "200")]  # all positive
    result_a, _ = execute_calculation_request(req)
    result_b, _ = execute_calculation_request(req)
    assert result_a.status == RESULT_STATUS_FAILED_CLOSED
    assert result_a.deterministic_input_hash == result_b.deterministic_input_hash
    assert result_a.result_id == result_b.result_id


def test_multiple_root_replay_is_deterministic():
    req = _xirr_request(request_id="req_multiroot_det")
    req["cash_flows"] = [
        _cf("2020-01-01", "-100"), _cf("2020-06-01", "1000"),
        _cf("2020-12-01", "-100"), _cf("2021-06-01", "-1000"),
    ]
    result_a, trace_a = execute_calculation_request(req)
    result_b, trace_b = execute_calculation_request(req)
    assert result_a.root_status == "MULTIPLE_ROOTS_POSSIBLE"
    assert result_a.deterministic_output_hash == result_b.deterministic_output_hash
    assert trace_a.trace_id == trace_b.trace_id


# --- Tamper detection (validation extended for dated calculators) -----------------

def test_valid_dated_result_passes_validation():
    result, trace = execute_calculation_request(_xirr_request())
    vr = validate_result(result, trace)
    assert vr.overall_status == "valid"


def test_tampered_dated_input_hash_detected():
    result, trace = execute_calculation_request(_xirr_request())
    tampered_trace = dataclasses.replace(trace, input_hash="0" * 64)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["input_hash_reproducible"] is False


def test_tampered_dated_output_hash_detected():
    result, trace = execute_calculation_request(_xirr_request())
    tampered_trace = dataclasses.replace(trace, output_hash="0" * 64)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["output_hash_matches"] is False


def test_tampered_dated_cash_flow_content_detected():
    # Tamper the actual normalized cash-flow content inside the trace's
    # dated_cash_flow_context, not just a hash string -- proves the check
    # recomputes from real content, not merely compares stored strings.
    result, trace = execute_calculation_request(_xirr_request())
    tampered_context = dict(trace.dated_cash_flow_context)
    tampered_cfs = [dict(cf) for cf in tampered_context["normalized_cash_flows"]]
    tampered_cfs[0]["amount"] = "-999999"
    tampered_context["normalized_cash_flows"] = tampered_cfs
    tampered_trace = dataclasses.replace(trace, dated_cash_flow_context=tampered_context)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["input_hash_reproducible"] is False


def test_tampered_dependency_fingerprint_detected():
    result, trace = execute_calculation_request(_xirr_request())
    tampered_context = dict(trace.dated_cash_flow_context)
    tampered_context["dependency_fingerprint"] = "pyxirr==9.9.9+FAKE_ADAPTER@9.9.9"
    tampered_trace = dataclasses.replace(trace, dated_cash_flow_context=tampered_context)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["dependency_fingerprint_matches"] is False


def test_tampered_root_status_inconsistent_with_sign_changes_detected():
    result, trace = execute_calculation_request(_xirr_request())  # single sign change -> SINGLE_ROOT
    tampered_context = dict(trace.dated_cash_flow_context)
    tampered_context["root_status"] = "MULTIPLE_ROOTS_POSSIBLE"  # false claim
    tampered_trace = dataclasses.replace(trace, dated_cash_flow_context=tampered_context)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["root_status_consistent_with_sign_changes"] is False


def test_tampered_xnpv_consistency_flag_detected():
    result, trace = execute_calculation_request(_xirr_request())
    tampered_context = dict(trace.dated_cash_flow_context)
    tampered_check = dict(tampered_context["xnpv_consistency_check"])
    tampered_check["within_tolerance"] = False  # false claim -- was actually True
    tampered_context["xnpv_consistency_check"] = tampered_check
    tampered_trace = dataclasses.replace(trace, dated_cash_flow_context=tampered_context)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["xnpv_consistency_within_tolerance"] is False


def test_xnpv_validation_has_no_root_status_or_xnpv_check_expectations():
    # XNPV_DATED has no root_status concept and no xnpv_consistency_check
    # of its own -- validation must not spuriously fail for their absence.
    result, trace = execute_calculation_request(_xnpv_request())
    vr = validate_result(result, trace)
    assert vr.overall_status == "valid"
    assert vr.checks["root_status_consistent_with_sign_changes"] is True
