"""
life_intelligence_lab.calculators.adapters.pyxirr_adapter
=============================================================

`PyXirrAdapter` is the ONLY place `pyxirr` is imported or called anywhere
in this codebase. Every calculator that needs a dated or periodic
cash-flow solve (`XNPV_DATED`, `XIRR_DATED`, `NPV_PERIODIC`,
`IRR_PERIODIC`) goes through this adapter's methods -- never through
`pyxirr` directly. `pyxirr`'s function names, exception types, and
None-vs-exception failure signals are all absorbed here; nothing outside
this module needs to know pyxirr exists.

Dependency identity:
    name:      pyxirr
    version:   captured live from the installed package at import time
    licence:   Unlicense (public domain equivalent) -- see PROTOTYPE_REPORT_003.md
    pinned:    pyxirr==0.10.8 in requirements.txt (sandbox-only; root
               dependency files are never touched)

Numerical boundary: pyxirr's Rust implementation requires native Python
`float`/`datetime.date` inputs -- it does not accept `Decimal`. This
adapter is therefore the ONE place in the whole calculator runtime where
a `Decimal` is deliberately converted to `float` before a solve, and
where the solved `float` result is converted back to `Decimal` (via
`Decimal(str(x))`, never `Decimal(x)`, to avoid re-introducing binary
-float noise beyond what the solver itself already introduced) on the
way out. Every other module in this runtime stays strictly Decimal.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal
from typing import Callable, List, Optional, Sequence, Tuple

import pyxirr

ADAPTER_ID = "life_intelligence_lab.calculators.adapters.pyxirr_adapter.PyXirrAdapter"
ADAPTER_VERSION = "pyxirr-adapter/0.1.0"
DEPENDENCY_NAME = "pyxirr"
PINNED_DEPENDENCY_VERSION = "0.10.8"  # matches requirements.txt; see PROTOTYPE_REPORT_003.md
INSTALLED_DEPENDENCY_VERSION = getattr(pyxirr, "__version__", "unknown")

# PolicyScna's day-count convention name -> pyxirr's DayCount enum member.
# This pinned pyxirr version's enum has NO plain "ACT_365" member; ACT_365F
# ("Actual/365 Fixed", i.e. days/365 with no leap-year adjustment) is the
# verified, standard match -- confirmed empirically to reproduce the exact
# expected known-answer XIRR vector before being relied on (see
# PROTOTYPE_REPORT_003.md section on the ACT_365 mapping).
_DAY_COUNT_MAP = {
    "ACT_365": pyxirr.DayCount.ACT_365F,
}


class DependencyFailureError(Exception):
    """
    Raised when the underlying engine call raises anything other than
    pyxirr's own expected `InvalidPaymentsError` domain signal (which is
    handled separately, since it represents a legitimate "your cash
    flows don't have a valid sign pattern" answer, not an engine
    failure). This is what section 18's "dependency adapter exception" /
    "simulated adapter failure" adversarial cases exercise.
    """


def dependency_fingerprint() -> str:
    return f"{DEPENDENCY_NAME}=={INSTALLED_DEPENDENCY_VERSION}+{ADAPTER_ID}@{ADAPTER_VERSION}"


def supported_day_count_conventions() -> Tuple[str, ...]:
    return tuple(_DAY_COUNT_MAP.keys())


def resolve_day_count(convention_name: str):
    if convention_name not in _DAY_COUNT_MAP:
        raise ValueError(f"unsupported_day_count_convention:{convention_name}")
    return _DAY_COUNT_MAP[convention_name]


@dataclasses.dataclass(frozen=True)
class SolveOutcome:
    """
    Uniform result shape for every adapter method: exactly one of
    `value` or `error_reason` is populated, and `raw_exception_type` is
    recorded (as a string, never the exception object itself) when the
    underlying engine raised something.
    """

    value: Optional[Decimal]
    converged: bool
    error_reason: Optional[str]
    raw_exception_type: Optional[str]


class PyXirrAdapter:
    """
    Instantiated with an injectable `engine` (defaults to the real
    `pyxirr` module) purely so tests can pass a fake engine that raises
    an arbitrary exception -- proving `DependencyFailureError` handling
    deterministically, without needing pyxirr itself to actually fail.
    This mirrors LIFE-PROTOTYPE-001's `fetch_fn` injection pattern.
    """

    def __init__(self, engine=pyxirr):
        self._engine = engine

    def xirr(
        self, dated_amounts: Sequence[Tuple[date, Decimal]], day_count_convention: str
    ) -> SolveOutcome:
        day_count = resolve_day_count(day_count_convention)
        dates_list = [d for d, _ in dated_amounts]
        amounts_list = [float(amount) for _, amount in dated_amounts]
        try:
            result = self._engine.xirr(dates_list, amounts_list, day_count=day_count)
        except getattr(self._engine, "InvalidPaymentsError", Exception) as exc:
            return SolveOutcome(value=None, converged=False, error_reason=str(exc), raw_exception_type="InvalidPaymentsError")
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: anything unexpected is a dependency failure
            raise DependencyFailureError(f"{type(exc).__name__}: {exc}") from exc

        if result is None:
            return SolveOutcome(value=None, converged=False, error_reason="no_root_found_or_non_convergent", raw_exception_type=None)
        return SolveOutcome(value=Decimal(str(result)), converged=True, error_reason=None, raw_exception_type=None)

    def xnpv(
        self, rate: Decimal, dated_amounts: Sequence[Tuple[date, Decimal]], day_count_convention: str
    ) -> SolveOutcome:
        day_count = resolve_day_count(day_count_convention)
        dates_list = [d for d, _ in dated_amounts]
        amounts_list = [float(amount) for _, amount in dated_amounts]
        try:
            result = self._engine.xnpv(float(rate), dates_list, amounts_list, day_count=day_count)
        except getattr(self._engine, "InvalidPaymentsError", Exception) as exc:
            return SolveOutcome(value=None, converged=False, error_reason=str(exc), raw_exception_type="InvalidPaymentsError")
        except Exception as exc:  # noqa: BLE001
            raise DependencyFailureError(f"{type(exc).__name__}: {exc}") from exc

        if result is None:
            # pyxirr.xnpv returns None (not an exception) for rate <= -1.
            return SolveOutcome(value=None, converged=False, error_reason="rate_out_of_domain_le_negative_one", raw_exception_type=None)
        return SolveOutcome(value=Decimal(str(result)), converged=True, error_reason=None, raw_exception_type=None)

    def irr_periodic(self, amounts: Sequence[Decimal]) -> SolveOutcome:
        amounts_list = [float(a) for a in amounts]
        try:
            result = self._engine.irr(amounts_list)
        except getattr(self._engine, "InvalidPaymentsError", Exception) as exc:
            return SolveOutcome(value=None, converged=False, error_reason=str(exc), raw_exception_type="InvalidPaymentsError")
        except Exception as exc:  # noqa: BLE001
            raise DependencyFailureError(f"{type(exc).__name__}: {exc}") from exc

        if result is None:
            return SolveOutcome(value=None, converged=False, error_reason="no_root_found_or_non_convergent", raw_exception_type=None)
        return SolveOutcome(value=Decimal(str(result)), converged=True, error_reason=None, raw_exception_type=None)

    def npv_periodic(self, rate: Decimal, amounts: Sequence[Decimal]) -> SolveOutcome:
        amounts_list = [float(a) for a in amounts]
        try:
            result = self._engine.npv(float(rate), amounts_list)
        except getattr(self._engine, "InvalidPaymentsError", Exception) as exc:
            return SolveOutcome(value=None, converged=False, error_reason=str(exc), raw_exception_type="InvalidPaymentsError")
        except Exception as exc:  # noqa: BLE001
            raise DependencyFailureError(f"{type(exc).__name__}: {exc}") from exc

        if result is None:
            return SolveOutcome(value=None, converged=False, error_reason="rate_out_of_domain", raw_exception_type=None)
        return SolveOutcome(value=Decimal(str(result)), converged=True, error_reason=None, raw_exception_type=None)


def count_sign_changes(ordered_amounts: Sequence[Decimal]) -> int:
    """
    Pure sign-change counter over already chronologically-ordered
    amounts, ignoring exact zeros (an inert flow neither confirms nor
    breaks a sign run). This is PolicyScna's own, fully deterministic,
    dependency-free multiple-root *indicator* -- not a root-finding
    algorithm -- used to decide whether a solved root should be reported
    as SINGLE_ROOT or MULTIPLE_ROOTS_POSSIBLE. See CALCULATOR_ARCHITECTURE.md.
    """
    non_zero_signs = [1 if a > 0 else -1 for a in ordered_amounts if a != 0]
    changes = 0
    for prev, curr in zip(non_zero_signs, non_zero_signs[1:]):
        if prev != curr:
            changes += 1
    return changes
