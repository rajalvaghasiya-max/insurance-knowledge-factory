"""
INFLATION_ADJUSTED_FV_APPROXIMATE: the `nominal_rate - inflation_rate`
shortcut. This is a SEPARATE, SEPARATELY REGISTERED calculator from
INFLATION_ADJUSTED_FV -- never a silent mode of the exact calculator --
specifically so a caller can never receive this approximation without
having deliberately selected a calculator whose id and every result
carries an explicit "this is not exact" warning.

    approximate_real_rate = nominal_rate - inflation_rate
    real_future_value = present_value * (1 + approximate_real_rate)^n

This is NOT the exact Fisher relationship
(real_rate = (1+nominal)/(1+inflation) - 1) and will diverge from it,
increasingly so at higher rates or longer horizons.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict

from life_intelligence_lab.calculators.formulas import FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_money

APPROXIMATION_WARNING = (
    "APPROXIMATE METHOD: uses (nominal_rate - inflation_rate) as a shortcut for the real "
    "rate. This is NOT the exact Fisher relationship and will diverge from the exact "
    "'INFLATION_ADJUSTED_FV' calculator's result, especially at higher rates or longer "
    "time horizons. Use INFLATION_ADJUSTED_FV for an exact result."
)


def compute(normalized: Dict[str, object]) -> FormulaOutput:
    pv: Decimal = normalized["present_value"]
    nominal_rate: Decimal = normalized["nominal_rate"]
    inflation_rate: Decimal = normalized["inflation_rate"]
    n: Decimal = normalized["periods"]
    n_int = int(n)

    approximate_real_rate = nominal_rate - inflation_rate
    growth_factor = (Decimal(1) + approximate_real_rate) ** n_int
    real_fv = pv * growth_factor

    steps = [
        FormulaStep(
            description="Compute the approximate real rate as (nominal_rate - inflation_rate)",
            expression=f"{nominal_rate} - {inflation_rate}",
            unrounded_value=approximate_real_rate,
        ),
        FormulaStep(
            description="Compute the growth factor (1 + approximate_real_rate)^periods",
            expression=f"(1 + {approximate_real_rate})^{n_int}",
            unrounded_value=growth_factor,
        ),
        FormulaStep(
            description="Multiply present value by the growth factor",
            expression=f"{pv} * {growth_factor}",
            unrounded_value=real_fv,
        ),
    ]

    real_fv_rounded = round_money(real_fv)

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"real_future_value": real_fv},
        output_after_rounding={"real_future_value": real_fv_rounded},
        warnings=[
            "This is a projection based on stated nominal-rate and inflation assumptions, not a guaranteed outcome.",
            APPROXIMATION_WARNING,
        ],
        rounding_applied={"real_future_value": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}},
    )
