"""
life_intelligence_lab.calculators.formulas
=============================================

Each module here implements exactly one registered calculator's formula.
A formula module is invoked ONLY by the runtime, ONLY with already
-normalized, decimal-safe inputs, and it returns a fully-populated set of
calculation steps -- it never receives raw request text and never
executes anything supplied by a caller. This is what makes "no
request-supplied formula text becomes executable" a structural property
rather than a policy statement (see ARCHITECTURE.md).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Dict, List


class DomainError(Exception):
    """
    Raised when a formula's mathematical domain is violated by otherwise
    well-typed, well-formed inputs (e.g. CAGR with a zero beginning
    value). Distinct from NormalizationError: normalization rejects
    malformed/ambiguous/incompatible input; DomainError rejects
    well-formed input that is mathematically undefined or unsupported
    for this specific formula. Both ultimately fail closed, but with
    different CalculationResult statuses (INVALID_INPUT vs FAILED_CLOSED)
    so a caller can tell "you gave me something malformed" apart from
    "you gave me something valid-looking that this formula cannot handle."

    `root_status`, new in LIFE-PROTOTYPE-003, optionally carries one of
    the ROOT_STATUS_* values (e.g. INVALID_CASH_FLOWS for an all-positive
    or all-negative XIRR request) through to `CalculationResult.root_status`
    even though a FAILED_CLOSED result has no trace and no numeric output
    -- root_status is metadata about *why* the computation could not
    proceed, never a plausible-looking result.
    """

    def __init__(self, message: str, root_status: str = None):
        super().__init__(message)
        self.root_status = root_status


@dataclasses.dataclass(frozen=True)
class FormulaStep:
    description: str
    expression: str
    unrounded_value: Decimal


@dataclasses.dataclass(frozen=True)
class FormulaOutput:
    """
    What every formula module's `compute()` returns to the runtime.
    `output_before_rounding` and `output_after_rounding` are both keyed
    identically by output field name; the runtime never rounds anything
    itself -- each formula module knows which of its own outputs are
    money (2dp) vs rate (6dp) and applies `rounding.py` accordingly, so
    rounding is declared once, at the source, not guessed downstream.

    `dated_cash_flow_context`, `dated_cash_flow_summary`, and
    `root_status` are new, optional fields (default `None`) used only by
    LIFE-PROTOTYPE-003's dated/periodic cash-flow calculators; every
    pre-existing Prototype 002 formula module leaves them unset.
    """

    steps: List[FormulaStep]
    output_before_rounding: Dict[str, Decimal]
    output_after_rounding: Dict[str, Decimal]
    warnings: List[str]
    rounding_applied: Dict[str, object]
    dated_cash_flow_context: dict = None
    dated_cash_flow_summary: dict = None
    root_status: str = None
