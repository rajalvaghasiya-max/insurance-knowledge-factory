"""
PV_LUMP_SUM: Present Value of a single future lump sum.

    PV = FV / (1 + r)^n

As with FV_LUMP_SUM, `n` is a non-negative integer, so Decimal's exact
integer-exponent power is used throughout.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict

from life_intelligence_lab.calculators.formulas import DomainError, FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_money


def compute(normalized: Dict[str, object]) -> FormulaOutput:
    fv: Decimal = normalized["future_value"]
    r: Decimal = normalized["periodic_rate"]
    n: Decimal = normalized["periods"]

    n_int = int(n)
    discount_factor = (Decimal(1) + r) ** n_int
    if discount_factor == 0:
        # Only reachable with r == -1 (a -100% periodic rate) and n != 0.
        raise DomainError("pv_discount_factor_zero: (1 + periodic_rate)^periods evaluates to zero")

    pv = fv / discount_factor

    steps = [
        FormulaStep(
            description="Compute the discount factor (1 + periodic_rate)^periods",
            expression=f"(1 + {r})^{n_int}",
            unrounded_value=discount_factor,
        ),
        FormulaStep(
            description="Divide future value by the discount factor",
            expression=f"{fv} / {discount_factor}",
            unrounded_value=pv,
        ),
    ]

    pv_rounded = round_money(pv)

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"present_value": pv},
        output_after_rounding={"present_value": pv_rounded},
        warnings=["This is a projection based on the stated rate and is not a guaranteed outcome."],
        rounding_applied={"present_value": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}},
    )
