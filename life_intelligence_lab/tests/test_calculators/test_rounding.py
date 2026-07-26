from decimal import Decimal

from life_intelligence_lab.calculators.rounding import round_money, round_rate_fraction, round_rate_percentage


# --- 29. Half-up monetary rounding --------------------------------------------------

def test_round_money_half_up_rounds_up_at_exact_half():
    assert round_money(Decimal("100.005")) == Decimal("100.01")
    assert round_money(Decimal("100.015")) == Decimal("100.02")


def test_round_money_half_up_does_not_round_down_at_half():
    # ROUND_HALF_UP must never round 0.005 down to 0.00 -- that would be
    # ROUND_HALF_EVEN (banker's rounding) instead, which is explicitly
    # NOT the documented policy here.
    assert round_money(Decimal("0.005")) == Decimal("0.01")


def test_round_money_default_two_decimal_places():
    assert round_money(Decimal("215892.49972727866982400000")) == Decimal("215892.50")


def test_round_rate_fraction_default_six_places():
    assert round_rate_fraction(Decimal("0.122462048309372981433533050")) == Decimal("0.122462")


def test_round_rate_percentage_default_four_places():
    assert round_rate_percentage(Decimal("12.2462048309372981433533050")) == Decimal("12.2462")


def test_unrounded_intermediate_values_preserved_in_trace():
    from life_intelligence_lab.calculators.runtime import execute_calculation_request

    request = {
        "request_id": "req_round_1",
        "calculator_id": "FV_LUMP_SUM",
        "calculator_version": 1,
        "calculation_date": "2026-07-26",
        "input_values": {"present_value": "100000", "periodic_rate": "8", "periods": "10"},
        "input_units": {"periodic_rate": "percentage"},
        "currency": "INR",
        "idempotency_key": "idem_round_1",
    }
    result, trace = execute_calculation_request(request)
    # The trace's output_before_rounding must retain full precision, not
    # already be truncated to 2dp.
    unrounded = trace.output_before_rounding["future_value"]
    assert unrounded != "215892.50"
    assert unrounded.startswith("215892.4997")
    assert trace.output_after_rounding["future_value"] == "215892.50"
