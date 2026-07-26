"""
XIRR_DATED: solves XNPV(r) = 0 for irregular, dated cash flows.

Domain rules (fail closed, DomainError -> FAILED_CLOSED with an explicit
root_status):
  - at least two normalized cash flows are required,
  - at least one positive and at least one negative amount are required,
  - a solver "no root" signal (pyxirr returning None) fails closed,
  - a genuine dependency exception is NOT caught here -- it propagates
    to the runtime, which maps it to FAILED_CLOSED with
    root_status=DEPENDENCY_FAILURE (see runtime.py).

Multiple-root handling: this module counts chronological sign changes in
the normalized (date-sorted) amounts itself -- a pure, dependency-free
indicator, not a root-finding algorithm. More than one sign change means
the returned rate is reported as a CANDIDATE only, tagged
root_status=MULTIPLE_ROOTS_POSSIBLE with an explicit warning; it is never
presented as uniquely correct merely because the pinned pyxirr version
happened to return a value for it.
"""

from __future__ import annotations

from datetime import date as _date
from decimal import Decimal
from typing import Dict, List

from life_intelligence_lab.calculators.adapters.pyxirr_adapter import (
    PyXirrAdapter,
    count_sign_changes,
    dependency_fingerprint,
)
from life_intelligence_lab.calculators.cash_flow import cash_flow_to_dict, duplicate_operation_to_dict
from life_intelligence_lab.calculators.contracts import (
    CashFlow,
    DuplicateDateOperation,
    ROOT_STATUS_INVALID_CASH_FLOWS,
    ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE,
    ROOT_STATUS_NO_ROOT_FOUND,
    ROOT_STATUS_SINGLE_ROOT,
)
from life_intelligence_lab.calculators.formulas import DomainError, FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_rate_fraction, round_rate_percentage

XNPV_CONSISTENCY_TOLERANCE = Decimal("0.01")  # absolute, in rate-adjacent monetary terms


def compute(
    normalized: Dict[str, object],
    method,
    cash_flows: List[CashFlow],
    duplicate_date_operations: List[DuplicateDateOperation],
    day_count_convention: str,
    duplicate_date_policy: str,
    currency: str,
    adapter: PyXirrAdapter = None,
) -> FormulaOutput:
    adapter = adapter or PyXirrAdapter()

    if len(cash_flows) < 2:
        raise DomainError(
            "xirr_requires_at_least_two_cash_flows", root_status=ROOT_STATUS_INVALID_CASH_FLOWS
        )

    amounts = [Decimal(cf.amount) for cf in cash_flows]
    if not any(a > 0 for a in amounts) or not any(a < 0 for a in amounts):
        raise DomainError(
            "xirr_requires_at_least_one_positive_and_one_negative_flow",
            root_status=ROOT_STATUS_INVALID_CASH_FLOWS,
        )

    sign_changes = count_sign_changes(amounts)
    dated_amounts = [(_date.fromisoformat(cf.date), Decimal(cf.amount)) for cf in cash_flows]

    outcome = adapter.xirr(dated_amounts, day_count_convention)

    if not outcome.converged:
        root_status = ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE if sign_changes > 1 else ROOT_STATUS_NO_ROOT_FOUND
        raise DomainError(f"xirr_no_root_found: {outcome.error_reason}", root_status=root_status)

    candidate_root = outcome.value
    root_status = ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE if sign_changes > 1 else ROOT_STATUS_SINGLE_ROOT

    xnpv_check_outcome = adapter.xnpv(candidate_root, dated_amounts, day_count_convention)
    xnpv_at_root = xnpv_check_outcome.value if xnpv_check_outcome.converged else None
    xnpv_within_tolerance = (
        xnpv_at_root is not None and abs(xnpv_at_root) <= XNPV_CONSISTENCY_TOLERANCE
    )

    warnings = []
    if root_status == ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE:
        warnings.append(
            f"MULTIPLE ROOTS POSSIBLE: {sign_changes} sign changes were detected in these cash "
            f"flows (chronological order). The returned rate is a CANDIDATE root only, not "
            f"guaranteed to be the unique or economically correct one. Do not treat it as "
            f"authoritative without independent review."
        )
    if not xnpv_within_tolerance:
        warnings.append(
            f"XNPV consistency check did not pass within tolerance ({XNPV_CONSISTENCY_TOLERANCE}): "
            f"XNPV at the candidate rate was {xnpv_at_root}."
        )

    rate_percentage = candidate_root * 100

    steps = [
        FormulaStep(
            description=f"Normalize {len(cash_flows)} dated cash flows and count chronological sign changes",
            expression=f"sign_changes({[str(a) for a in amounts]}) = {sign_changes}",
            unrounded_value=Decimal(sign_changes),
        ),
        FormulaStep(
            description=f"Solve XNPV(r) = 0 via the contained PyXirrAdapter (day-count: {day_count_convention})",
            expression=f"xirr({[cf.date for cf in cash_flows]}, {[str(a) for a in amounts]})",
            unrounded_value=candidate_root,
        ),
        FormulaStep(
            description="XNPV consistency check at the candidate rate (should be ~0)",
            expression=f"xnpv({candidate_root}, ...)",
            unrounded_value=xnpv_at_root if xnpv_at_root is not None else Decimal("NaN"),
        ),
    ]

    dated_cash_flow_context = {
        "original_cash_flows": [cash_flow_to_dict(cf) for cf in sorted(cash_flows, key=lambda c: c.sequence)],
        "normalized_cash_flows": [cash_flow_to_dict(cf) for cf in cash_flows],
        "duplicate_date_policy": duplicate_date_policy,
        "duplicate_date_operations": [duplicate_operation_to_dict(op) for op in duplicate_date_operations],
        "base_date": cash_flows[0].date,
        "day_count_convention": day_count_convention,
        "year_fractions": [
            {"cash_flow_id": cf.cash_flow_id, "date": cf.date,
             "year_fraction": str((_date.fromisoformat(cf.date) - _date.fromisoformat(cash_flows[0].date)).days / 365)}
            for cf in cash_flows
        ],
        "solver_adapter_id": "life_intelligence_lab.calculators.adapters.pyxirr_adapter.PyXirrAdapter",
        "solver_adapter_version": "pyxirr-adapter/0.1.0",
        "dependency_name": "pyxirr",
        "dependency_version": __import__("pyxirr").__version__,
        "dependency_fingerprint": dependency_fingerprint(),
        "solver_status": "converged" if outcome.converged else "not_converged",
        "root_search_bounds": None,  # pyxirr's internal solver bounds are not exposed to this adapter
        "candidate_roots": [str(candidate_root)],
        "selected_candidate_root": str(candidate_root),
        "root_status": root_status,
        "convergence_info": {"converged": outcome.converged},
        "tolerance": str(XNPV_CONSISTENCY_TOLERANCE),
        "solver_warnings": warnings,
        "xnpv_consistency_check": {
            "xnpv_at_root": str(xnpv_at_root) if xnpv_at_root is not None else None,
            "tolerance": str(XNPV_CONSISTENCY_TOLERANCE),
            "within_tolerance": xnpv_within_tolerance,
        },
    }

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
        dated_cash_flow_context=dated_cash_flow_context,
        dated_cash_flow_summary={
            "root_status": root_status,
            "day_count_convention": day_count_convention,
            "duplicate_date_policy": duplicate_date_policy,
        },
        root_status=root_status,
    )
