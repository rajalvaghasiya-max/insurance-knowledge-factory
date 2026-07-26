"""
NPV_PERIODIC: net present value for a plain, undated, regular-period
sequence of cash flows, at a caller-supplied rate.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from life_intelligence_lab.calculators.adapters.pyxirr_adapter import PyXirrAdapter
from life_intelligence_lab.calculators.formulas import DomainError, FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_money


def compute(normalized: Dict[str, object], method, adapter: PyXirrAdapter = None) -> FormulaOutput:
    adapter = adapter or PyXirrAdapter()
    rate: Decimal = normalized["rate"]
    amounts: List[Decimal] = normalized["cash_flows"]

    if rate <= -1:
        raise DomainError(f"npv_periodic_rate_out_of_domain: rate ({rate}) must be greater than -1")
    if len(amounts) < 1:
        raise DomainError("npv_periodic_requires_at_least_one_flow")

    outcome = adapter.npv_periodic(rate, amounts)
    if not outcome.converged:
        raise DomainError(f"npv_periodic_evaluation_failed: {outcome.error_reason}")

    npv_value = outcome.value

    steps = [
        FormulaStep(
            description=f"Evaluate periodic NPV at rate {rate} over {len(amounts)} flows",
            expression=f"npv({rate}, {[str(a) for a in amounts]})",
            unrounded_value=npv_value,
        ),
    ]

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"npv": npv_value},
        output_after_rounding={"npv": round_money(npv_value)},
        warnings=[],
        rounding_applied={"npv": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}},
        dated_cash_flow_context=None,
        dated_cash_flow_summary=None,
        root_status=None,
    )
