import json

from life_intelligence_lab.calculators import canonical, serialization
from life_intelligence_lab.calculators.contracts import (
    CALCULATION_RESULT_FIELD_ORDER,
    CALCULATION_TRACE_FIELD_ORDER,
)
from life_intelligence_lab.calculators.runtime import execute_calculation_request


def _fv_request():
    return {
        "request_id": "req_det_1",
        "calculator_id": "FV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": "100000", "periodic_rate": "8", "periods": "10"},
        "input_units": {"periodic_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": "idem_det_1",
    }


# --- 21. Deterministic input hash --------------------------------------------------

def test_deterministic_input_hash_stable_across_runs():
    result_a, _ = execute_calculation_request(_fv_request())
    result_b, _ = execute_calculation_request(_fv_request())
    assert result_a.deterministic_input_hash == result_b.deterministic_input_hash
    assert result_a.deterministic_input_hash is not None


def test_input_hash_changes_when_input_changes():
    request_a = _fv_request()
    request_b = _fv_request()
    request_b["input_values"]["present_value"] = "200000"
    result_a, _ = execute_calculation_request(request_a)
    result_b, _ = execute_calculation_request(request_b)
    assert result_a.deterministic_input_hash != result_b.deterministic_input_hash


# --- 22. Deterministic result hash ---------------------------------------------------

def test_deterministic_result_content_hash_stable_across_runs():
    result_a, _ = execute_calculation_request(_fv_request())
    result_b, _ = execute_calculation_request(_fv_request())
    hash_a = canonical.hash_result_content(serialization.result_to_dict(result_a), CALCULATION_RESULT_FIELD_ORDER)
    hash_b = canonical.hash_result_content(serialization.result_to_dict(result_b), CALCULATION_RESULT_FIELD_ORDER)
    assert hash_a == hash_b


# --- 23. Deterministic trace hash ----------------------------------------------------

def test_deterministic_trace_content_hash_stable_across_runs():
    _, trace_a = execute_calculation_request(_fv_request())
    _, trace_b = execute_calculation_request(_fv_request())
    hash_a = canonical.hash_trace_content(serialization.trace_to_dict(trace_a), CALCULATION_TRACE_FIELD_ORDER)
    hash_b = canonical.hash_trace_content(serialization.trace_to_dict(trace_b), CALCULATION_TRACE_FIELD_ORDER)
    assert hash_a == hash_b


# --- 24. Repeated execution produces byte-identical canonical output -----------------

def test_repeated_execution_produces_byte_identical_json():
    result_a, trace_a = execute_calculation_request(_fv_request())
    result_b, trace_b = execute_calculation_request(_fv_request())

    result_json_a = json.dumps(serialization.result_to_dict(result_a), sort_keys=False)
    result_json_b = json.dumps(serialization.result_to_dict(result_b), sort_keys=False)
    assert result_json_a == result_json_b

    trace_json_a = json.dumps(serialization.trace_to_dict(trace_a), sort_keys=False)
    trace_json_b = json.dumps(serialization.trace_to_dict(trace_b), sort_keys=False)
    assert trace_json_a == trace_json_b

    # Ids themselves must be identical too (content-derived, not random).
    assert result_a.result_id == result_b.result_id
    assert trace_a.trace_id == trace_b.trace_id


# --- 30. No timestamp randomness in deterministic content ----------------------------

def test_no_timestamp_or_random_fields_in_result_or_trace_content():
    result, trace = execute_calculation_request(_fv_request())
    result_dict = serialization.result_to_dict(result)
    trace_dict = serialization.trace_to_dict(trace)

    # Serialize and scan for anything resembling a wall-clock timestamp
    # (ISO date-times contain 'T' between date and time, plus a colon).
    combined_text = json.dumps(result_dict) + json.dumps(trace_dict)
    assert "T" not in combined_text or ":" not in combined_text.split("T", 1)[-1][:9]
    # More directly: neither dataclass has any field literally named for
    # a timestamp or a random id.
    assert "timestamp" not in "".join(CALCULATION_RESULT_FIELD_ORDER)
    assert "timestamp" not in "".join(CALCULATION_TRACE_FIELD_ORDER)


def test_ids_are_content_derived_not_random_uuids():
    result, trace = execute_calculation_request(_fv_request())
    # A random uuid4 has dashes in the classic 8-4-4-4-12 pattern; our ids
    # are "result_<hexhex>_<hexhex>" / "trace_<hexhex>_<hexhex>" instead.
    assert result.result_id.startswith("result_")
    assert trace.trace_id.startswith("trace_")
    assert "-" not in result.result_id
    assert "-" not in trace.trace_id
