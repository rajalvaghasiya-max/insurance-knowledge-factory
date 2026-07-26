"""
IRR_PERIODIC: internal rate of return for a plain, undated, regular
-period sequence of cash flows (index 0, 1, 2, ... n-1).

Deliberately separate terminology and mechanism from XIRR_DATED -- no
dates, no day-count convention, no duplicate-date policy. Flows arrive
as a single `cash_flows` decimal-list input (see normalization.py's
FIELD_KIND_DECIMAL_LIST), not via CalculationRequest.cash_flows (which
is reserved for the dated CashFlow contract).

Domain rules (fail closed, same discipline as XIRR_DATED):
  - at least two flows,
  - at least one positive and one negative amount,
  - solver "no root" fails closed,
  - more than one sign change -> MULTIPLE_ROOTS_POSSIBLE, candidate only.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from life_intelligence_lab.calculators.adapters.pyxirr_adapter import PyXirrAdapter, count_sign_changes
from life_intelligence_lab.calculators.contracts import (
    ROOT_STATUS_INVALID_CASH_FLOWS,
    ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE,
    ROOT_STATUS_NO_ROOT_FOUND,
    ROOT_STATUS_SINGLE_ROOT,
)
from life_intelligence_lab.calculators.formulas import DomainError, FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_rate_fraction, round_rate_percentage


def compute(normalized: Dict[str, object], method, adapter: PyXirrAdapter = None) -> FormulaOutput:
    adapter = adapter or PyXirrAdapter()
    amounts: List[Decimal] = normalized["cash_flows"]

    if len(amounts) < 2:
        raise DomainError("irr_periodic_requires_at_least_two_flows", root_status=ROOT_STATUS_INVALID_CASH_FLOWS)
    if not any(a > 0 for a in amounts) or not any(a < 0 for a in amounts):
        raise DomainError(
            "irr_periodic_requires_at_least_one_positive_and_one_negative_flow",
            root_status=ROOT_STATUS_INVALID_CASH_FLOWS,
        )

    sign_changes = count_sign_changes(amounts)
    outcome = adapter.irr_periodic(amounts)

    if not outcome.converged:
        root_status = ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE if sign_changes > 1 else ROOT_STATUS_NO_ROOT_FOUND
        raise DomainError(f"irr_periodic_no_root_found: {outcome.error_reason}", root_status=root_status)

    candidate_root = outcome.value
    root_status = ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE if sign_changes > 1 else ROOT_STATUS_SINGLE_ROOT

    warnings = []
    if root_status == ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE:
        warnings.append(
            f"MULTIPLE ROOTS POSSIBLE: {sign_changes} sign changes were detected in these periodic "
            f"cash flows. The returned rate is a CANDIDATE root only, not guaranteed unique."
        )

    rate_percentage = candidate_root * 100

    steps = [
        FormulaStep(
            description=f"Count sign changes across {len(amounts)} periodic flows",
            expression=f"sign_changes({[str(a) for a in amounts]}) = {sign_changes}",
            unrounded_value=Decimal(sign_changes),
        ),
        FormulaStep(
            description="Solve periodic IRR via the contained PyXirrAdapter",
            expression=f"irr({[str(a) for a in amounts]})",
            unrounded_value=candidate_root,
        ),
    ]

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"rate": candidate_root, "rate_percentage": rate_percentage},
        output_after_rounding={
            "rate": round_rate_fraction(candidate_root),
            "rate_percentage": round_rate_percentage(rate_percentage),
        },
        warnings=warnings,
        rounding_applied={
            "rate": {"decimal_places": 6, "mode": "ROUND_HALF_UP"},
            "rate_percentage": {"decimal_places": 4, "mode": "ROUND_HALF_UP"},
        },
        dated_cash_flow_context=None,
        dated_cash_flow_summary={"root_status": root_status},
        root_status=root_status,
    )
