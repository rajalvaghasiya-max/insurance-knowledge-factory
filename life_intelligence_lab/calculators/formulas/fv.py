"""
FV_LUMP_SUM: Future Value of a single lump sum.

    FV = PV * (1 + r)^n

`n` is always a non-negative integer period count in this prototype, so
Decimal's exact integer-exponent power is used throughout -- no
fractional exponent, no float boundary is ever crossed for this formula.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict

from life_intelligence_lab.calculators.formulas import FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_money


def compute(normalized: Dict[str, object]) -> FormulaOutput:
    pv: Decimal = normalized["present_value"]
    r: Decimal = normalized["periodic_rate"]
    n: Decimal = normalized["periods"]  # already validated as a non-negative integer-valued Decimal

    n_int = int(n)
    growth_factor = (Decimal(1) + r) ** n_int
    fv = pv * growth_factor

    steps = [
        FormulaStep(
            description="Compute the compound growth factor (1 + periodic_rate)^periods",
            expression=f"(1 + {r})^{n_int}",
            unrounded_value=growth_factor,
        ),
        FormulaStep(
            description="Multiply present value by the growth factor",
            expression=f"{pv} * {growth_factor}",
            unrounded_value=fv,
        ),
    ]

    fv_rounded = round_money(fv)

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"future_value": fv},
        output_after_rounding={"future_value": fv_rounded},
        warnings=["This is a projection based on the stated rate and is not a guaranteed outcome."],
        rounding_applied={"future_value": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}},
    )
