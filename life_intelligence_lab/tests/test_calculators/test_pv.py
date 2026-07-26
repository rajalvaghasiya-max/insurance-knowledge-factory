from life_intelligence_lab.calculators.contracts import RESULT_STATUS_SUCCESS
from life_intelligence_lab.calculators.runtime import execute_calculation_request


# --- 3. Present value known-answer vector ------------------------------------

def test_pv_known_answer_vector():
    request = {
        "request_id": "req_pv_1",
        "calculator_id": "PV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"future_value": "1000000", "periodic_rate": "7", "periods": "15"},
        "input_units": {"periodic_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": "idem_pv_1",
    }
    result, trace = execute_calculation_request(request)
    assert result.status == RESULT_STATUS_SUCCESS
    assert result.output_values["present_value"] == "362446.02"
