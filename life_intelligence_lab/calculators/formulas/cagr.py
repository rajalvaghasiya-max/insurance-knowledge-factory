"""
CAGR: Compound Annual Growth Rate.

    CAGR = (ending_value / beginning_value)^(1/n) - 1

Domain rules (fail closed, DomainError -> CalculationResult status
FAILED_CLOSED):
  - beginning_value must not be zero (division by zero).
  - beginning_value or ending_value negative is rejected UNLESS the
    caller explicitly sets allow_negative_values=true.
  - periods must be a positive integer (1/n is undefined at n=0; a
    negative period count is already rejected generically at
    normalization, before this formula ever runs).
  - even with allow_negative_values=true, a negative ratio raised to a
    fractional power has no real result and is rejected.

`1/n` is a genuinely fractional exponent (unlike FV/PV/PV's integer `n`),
so this is the one formula in this prototype where Decimal's fractional-
power support is actually exercised -- see ARCHITECTURE.md for why this
stays inside Decimal rather than crossing into float.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict

from life_intelligence_lab.calculators.formulas import DomainError, FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_rate_fraction, round_rate_percentage


def compute(normalized: Dict[str, object]) -> FormulaOutput:
    beginning: Decimal = normalized["beginning_value"]
    ending: Decimal = normalized["ending_value"]
    n: Decimal = normalized["periods"]
    allow_negative = bool(normalized.get("allow_negative_values", False))

    if beginning == 0:
        raise DomainError("cagr_beginning_value_zero: beginning value cannot be zero")
    n_int = int(n)
    if n_int <= 0:
        raise DomainError("cagr_periods_must_be_positive: periods must be greater than zero")
    if not allow_negative and (beginning < 0 or ending < 0):
        raise DomainError(
            "cagr_negative_value_not_supported: negative beginning/ending value requires "
            "allow_negative_values=true"
        )

    ratio = ending / beginning
    exponent = Decimal(1) / Decimal(n_int)

    try:
        growth_factor = ratio ** exponent
    except InvalidOperation:
        raise DomainError(
            "cagr_undefined_for_input_combination: the ratio raised to a fractional power "
            "has no real result for these inputs"
        ) from None

    cagr = growth_factor - 1

    steps = [
        FormulaStep(
            description="Compute the ratio of ending value to beginning value",
            expression=f"{ending} / {beginning}",
            unrounded_value=ratio,
        ),
        FormulaStep(
            description="Raise the ratio to the power of (1 / periods)",
            expression=f"({ratio})^(1/{n_int})",
            unrounded_value=growth_factor,
        ),
        FormulaStep(
            description="Subtract 1 to obtain the compound annual growth rate",
            expression=f"{growth_factor} - 1",
            unrounded_value=cagr,
        ),
    ]

    cagr_rounded = round_rate_fraction(cagr)
    cagr_percentage_rounded = round_rate_percentage(cagr * 100)

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"cagr": cagr, "cagr_percentage": cagr * 100},
        output_after_rounding={"cagr": cagr_rounded, "cagr_percentage": cagr_percentage_rounded},
        warnings=["CAGR smooths an irregular growth path into a single annualized figure; it is not a guaranteed future rate."],
        rounding_applied={
            "cagr": {"decimal_places": 6, "mode": "ROUND_HALF_UP"},
            "cagr_percentage": {"decimal_places": 4, "mode": "ROUND_HALF_UP"},
        },
    )
