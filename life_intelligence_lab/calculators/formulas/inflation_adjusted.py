"""
INFLATION_ADJUSTED_FV: Real (inflation-adjusted) future value, exact methods only.

Supports exactly two named, mathematically equivalent methods -- the
caller MUST select one explicitly via CalculationRequest.method; there is
no default, so no convention is ever silently chosen.

Method A -- "deflate_nominal":
    nominal_future_value = present_value * (1 + nominal_rate)^n
    real_future_value = nominal_future_value / (1 + inflation_rate)^n

Method B -- "exact_real_rate":
    real_rate = (1 + nominal_rate) / (1 + inflation_rate) - 1
    real_future_value = present_value * (1 + real_rate)^n

Both are the same Fisher relationship approached from two directions and
will agree to within Decimal rounding. NEITHER of these is the
approximate `nominal_rate - inflation_rate` shortcut -- that lives in a
separate, separately-named calculator (`inflation_adjusted_approx.py`),
never as a silent option here.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict

from life_intelligence_lab.calculators.formulas import FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_money

METHOD_DEFLATE_NOMINAL = "deflate_nominal"
METHOD_EXACT_REAL_RATE = "exact_real_rate"
SUPPORTED_METHODS = (METHOD_DEFLATE_NOMINAL, METHOD_EXACT_REAL_RATE)


def compute(normalized: Dict[str, object], method: str) -> FormulaOutput:
    pv: Decimal = normalized["present_value"]
    nominal_rate: Decimal = normalized["nominal_rate"]
    inflation_rate: Decimal = normalized["inflation_rate"]
    n: Decimal = normalized["periods"]
    n_int = int(n)

    if method == METHOD_DEFLATE_NOMINAL:
        nominal_growth = (Decimal(1) + nominal_rate) ** n_int
        nominal_fv = pv * nominal_growth
        inflation_discount = (Decimal(1) + inflation_rate) ** n_int
        real_fv = nominal_fv / inflation_discount

        steps = [
            FormulaStep(
                description="Compute nominal growth factor (1 + nominal_rate)^periods",
                expression=f"(1 + {nominal_rate})^{n_int}",
                unrounded_value=nominal_growth,
            ),
            FormulaStep(
                description="Compute nominal future value",
                expression=f"{pv} * {nominal_growth}",
                unrounded_value=nominal_fv,
            ),
            FormulaStep(
                description="Compute inflation discount factor (1 + inflation_rate)^periods",
                expression=f"(1 + {inflation_rate})^{n_int}",
                unrounded_value=inflation_discount,
            ),
            FormulaStep(
                description="Deflate the nominal future value by the inflation discount factor",
                expression=f"{nominal_fv} / {inflation_discount}",
                unrounded_value=real_fv,
            ),
        ]

    elif method == METHOD_EXACT_REAL_RATE:
        real_rate = (Decimal(1) + nominal_rate) / (Decimal(1) + inflation_rate) - 1
        real_growth = (Decimal(1) + real_rate) ** n_int
        real_fv = pv * real_growth

        steps = [
            FormulaStep(
                description="Compute the exact real rate via the Fisher relationship",
                expression=f"(1 + {nominal_rate}) / (1 + {inflation_rate}) - 1",
                unrounded_value=real_rate,
            ),
            FormulaStep(
                description="Compute the real growth factor (1 + real_rate)^periods",
                expression=f"(1 + {real_rate})^{n_int}",
                unrounded_value=real_growth,
            ),
            FormulaStep(
                description="Multiply present value by the real growth factor",
                expression=f"{pv} * {real_growth}",
                unrounded_value=real_fv,
            ),
        ]

    else:  # pragma: no cover -- runtime.normalize_method() guarantees this cannot happen
        raise ValueError(f"unsupported method reached formula module: {method}")

    real_fv_rounded = round_money(real_fv)

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"real_future_value": real_fv},
        output_after_rounding={"real_future_value": real_fv_rounded},
        warnings=[
            "This is a projection based on stated nominal-rate and inflation assumptions, not a guaranteed outcome.",
            f"Computed using the exact '{method}' method.",
        ],
        rounding_applied={"real_future_value": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}},
    )
