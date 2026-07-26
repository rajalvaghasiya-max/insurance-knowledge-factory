import dataclasses

from life_intelligence_lab.calculators.runtime import execute_calculation_request
from life_intelligence_lab.calculators.validation import validate_result


def _fv_request():
    return {
        "request_id": "req_val_1",
        "calculator_id": "FV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": "100000", "periodic_rate": "8", "periods": "10"},
        "input_units": {"periodic_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": "idem_val_1",
    }


def test_valid_success_result_passes_validation():
    result, trace = execute_calculation_request(_fv_request())
    vr = validate_result(result, trace)
    assert vr.overall_status == "valid"
    assert all(vr.checks.values())


# --- 25. Result without trace fails validation ----------------------------------------

def test_success_result_without_trace_fails_validation():
    result, trace = execute_calculation_request(_fv_request())
    vr = validate_result(result, None)  # SUCCESS status, but no trace supplied
    assert vr.overall_status == "invalid"
    assert any("trace_missing_for_success" in reason for reason in vr.reasons)


# --- 26. Trace/result mismatch fails validation ---------------------------------------

def test_trace_result_id_mismatch_fails_validation():
    result, trace = execute_calculation_request(_fv_request())
    mismatched_trace = dataclasses.replace(trace, trace_id="trace_does_not_match_result")
    vr = validate_result(result, mismatched_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["result_references_correct_trace"] is False


# --- 27. Tampered input hash detected --------------------------------------------------

def test_tampered_trace_input_hash_detected():
    result, trace = execute_calculation_request(_fv_request())
    tampered_trace = dataclasses.replace(trace, input_hash="0" * 64)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["input_hash_reproducible"] is False


def test_tampered_result_input_hash_detected():
    result, trace = execute_calculation_request(_fv_request())
    tampered_result = dataclasses.replace(result, deterministic_input_hash="0" * 64)
    vr = validate_result(tampered_result, trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["input_hash_reproducible"] is False


# --- 28. Tampered output hash detected --------------------------------------------------

def test_tampered_trace_output_hash_detected():
    result, trace = execute_calculation_request(_fv_request())
    tampered_trace = dataclasses.replace(trace, output_hash="0" * 64)
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["output_hash_matches"] is False


def test_tampered_output_values_detected_via_output_hash():
    # A tampered *value* (not just a tampered hash string) must also be
    # caught, since the hash is recomputed from the trace's own content,
    # not merely compared against a stored hash string.
    result, trace = execute_calculation_request(_fv_request())
    tampered_trace = dataclasses.replace(
        trace, output_after_rounding={"future_value": "999999.99"}
    )
    vr = validate_result(result, tampered_trace)
    assert vr.overall_status == "invalid"
    assert vr.checks["output_hash_matches"] is False


def test_non_success_result_with_unexpected_trace_fails_validation():
    from life_intelligence_lab.calculators.contracts import RESULT_STATUS_UNSUPPORTED_CALCULATOR
    result, trace = execute_calculation_request(_fv_request())
    fake_failed_result = dataclasses.replace(
        result, status=RESULT_STATUS_UNSUPPORTED_CALCULATOR, reason="unknown_calculator_id"
    )
    vr = validate_result(fake_failed_result, trace)  # trace should not exist for this status
    assert vr.overall_status == "invalid"
