"""
XNPV_DATED: XNPV(r) = sum_i CF_i / (1 + r)^year_fraction(d0, di)

Unlike XIRR, the rate is a caller-supplied input here, not solved for --
this is a straightforward evaluation, not a root search, so there is no
root-status concept for this calculator (root_status stays None).

Domain rules (fail closed):
  - rate <= -1 is mathematically undefined for this formula (the pinned
    pyxirr version signals this by returning None, not an exception --
    see PyXirrAdapter's docstring) and fails closed here.
"""

from __future__ import annotations

from datetime import date as _date
from decimal import Decimal
from typing import Dict, List

from life_intelligence_lab.calculators.adapters.pyxirr_adapter import PyXirrAdapter, dependency_fingerprint
from life_intelligence_lab.calculators.cash_flow import cash_flow_to_dict, duplicate_operation_to_dict
from life_intelligence_lab.calculators.contracts import CashFlow, DuplicateDateOperation
from life_intelligence_lab.calculators.formulas import DomainError, FormulaOutput, FormulaStep
from life_intelligence_lab.calculators.rounding import round_money


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

    rate: Decimal = normalized["rate"]
    if rate <= -1:
        raise DomainError(f"xnpv_rate_out_of_domain: rate ({rate}) must be greater than -1")

    if len(cash_flows) < 1:
        raise DomainError("xnpv_requires_at_least_one_cash_flow")

    dated_amounts = [(_date.fromisoformat(cf.date), Decimal(cf.amount)) for cf in cash_flows]
    outcome = adapter.xnpv(rate, dated_amounts, day_count_convention)

    if not outcome.converged:
        raise DomainError(f"xnpv_evaluation_failed: {outcome.error_reason}")

    xnpv_value = outcome.value

    steps = [
        FormulaStep(
            description=f"Evaluate XNPV at rate {rate} over {len(cash_flows)} dated cash flows (day-count: {day_count_convention})",
            expression=f"xnpv({rate}, {[cf.date for cf in cash_flows]}, {[cf.amount for cf in cash_flows]})",
            unrounded_value=xnpv_value,
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
        "solver_status": "converged",
        "root_search_bounds": None,
        "candidate_roots": [],
        "selected_candidate_root": None,
        "root_status": None,
        "convergence_info": {"converged": True},
        "tolerance": None,
        "solver_warnings": [],
        "xnpv_consistency_check": None,
    }

    return FormulaOutput(
        steps=steps,
        output_before_rounding={"xnpv": xnpv_value},
        output_after_rounding={"xnpv": round_money(xnpv_value)},
        warnings=[],
        rounding_applied={"xnpv": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}},
        dated_cash_flow_context=dated_cash_flow_context,
        dated_cash_flow_summary={
            "day_count_convention": day_count_convention,
            "duplicate_date_policy": duplicate_date_policy,
        },
        root_status=None,
    )
