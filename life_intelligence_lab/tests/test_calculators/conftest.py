import pytest


@pytest.fixture
def fv_base_request():
    return {
        "request_id": "req_fv_base",
        "calculator_id": "FV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": "100000", "periodic_rate": "8", "periods": "10"},
        "input_units": {"periodic_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": "idem_fv_base",
    }
