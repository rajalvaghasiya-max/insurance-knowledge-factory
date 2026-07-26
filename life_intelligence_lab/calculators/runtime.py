"""
life_intelligence_lab.calculators.runtime
=============================================

The deterministic orchestrator:

    CalculationRequest -> calculator registry lookup -> input normalization
    -> deterministic calculation -> CalculationTrace -> CalculationResult

`execute_calculation_request` is a pure function of its input dict (plus
the fixed, code-defined registry and formula dispatch table below) --
calling it twice with the same request produces byte-identical results,
which is what both the run and replay CLIs, and every determinism test,
rely on.

The formula dispatch table below is fixed, code-defined data -- NOT
constructed from anything in the request. A request can only ever select
among these pre-registered (calculator_id, calculator_version) pairs; it
can never supply, reference, or trigger execution of arbitrary formula
text. This is what makes "no request-supplied formula text becomes
executable" a structural property of the dispatch mechanism, not a rule
that has to be remembered and enforced elsewhere.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Dict, Optional, Tuple

from life_intelligence_lab.calculators import canonical, registry
from life_intelligence_lab.calculators.adapters.pyxirr_adapter import DependencyFailureError
from life_intelligence_lab.calculators.cash_flow import normalize_cash_flow_list
from life_intelligence_lab.calculators.contracts import (
    CALCULATOR_STATUS_RETIRED,
    ROOT_STATUS_DEPENDENCY_FAILURE,
    CalculationResult,
    CalculationStep,
    CalculationTrace,
    RESULT_STATUS_FAILED_CLOSED,
    RESULT_STATUS_INVALID_INPUT,
    RESULT_STATUS_SUCCESS,
    RESULT_STATUS_UNSUPPORTED_CALCULATOR,
    RUNTIME_VERSION,
)
from life_intelligence_lab.calculators.formulas import DomainError, FormulaOutput
from life_intelligence_lab.calculators.formulas import cagr as cagr_formula
from life_intelligence_lab.calculators.formulas import fv as fv_formula
from life_intelligence_lab.calculators.formulas import inflation_adjusted
from life_intelligence_lab.calculators.formulas import inflation_adjusted_approx
from life_intelligence_lab.calculators.formulas import irr_periodic as irr_periodic_formula
from life_intelligence_lab.calculators.formulas import npv_periodic as npv_periodic_formula
from life_intelligence_lab.calculators.formulas import pv as pv_formula
from life_intelligence_lab.calculators.formulas import xirr as xirr_formula
from life_intelligence_lab.calculators.formulas import xnpv as xnpv_formula
from life_intelligence_lab.calculators.normalization import (
    NormalizationError,
    normalize_method,
    normalize_request_inputs,
    normalized_inputs_to_decimal_map,
    normalized_inputs_to_dict,
    validate_currency,
)

_REQUIRED_ENVELOPE_FIELDS = ("request_id", "calculator_id", "calculator_version", "calculation_date", "idempotency_key")

# Fixed, code-defined dispatch table: calculator_id -> compute function.
# This is the only place a calculator_id is ever translated into
# executable code, and it is not influenced by anything in the request.
#
# Every entry now takes a uniform (normalized, method, context) signature.
# `context` carries the dated-cash-flow-specific extras (normalized
# CashFlow list, duplicate-date operations, day-count convention) for
# XIRR_DATED/XNPV_DATED; every pre-existing Prototype 002 calculator
# simply ignores it (context is always `{}` for them).
_DISPATCH: Dict[str, Callable] = {
    "FV_LUMP_SUM": lambda normalized, method, context: fv_formula.compute(normalized),
    "PV_LUMP_SUM": lambda normalized, method, context: pv_formula.compute(normalized),
    "CAGR": lambda normalized, method, context: cagr_formula.compute(normalized),
    "INFLATION_ADJUSTED_FV": lambda normalized, method, context: inflation_adjusted.compute(normalized, method),
    "INFLATION_ADJUSTED_FV_APPROX": lambda normalized, method, context: inflation_adjusted_approx.compute(normalized),
    "XIRR_DATED": lambda normalized, method, context: xirr_formula.compute(
        normalized, method,
        cash_flows=context["cash_flows"],
        duplicate_date_operations=context["duplicate_date_operations"],
        day_count_convention=context["day_count_convention"],
        duplicate_date_policy=context["duplicate_date_policy"],
        currency=context["currency"],
    ),
    "XNPV_DATED": lambda normalized, method, context: xnpv_formula.compute(
        normalized, method,
        cash_flows=context["cash_flows"],
        duplicate_date_operations=context["duplicate_date_operations"],
        day_count_convention=context["day_count_convention"],
        duplicate_date_policy=context["duplicate_date_policy"],
        currency=context["currency"],
    ),
    "IRR_PERIODIC": lambda normalized, method, context: irr_periodic_formula.compute(normalized, method),
    "NPV_PERIODIC": lambda normalized, method, context: npv_periodic_formula.compute(normalized, method),
}


def _envelope_error_result(request: dict, reason: str) -> CalculationResult:
    request_id = str(request.get("request_id", "unknown"))
    calculator_id = str(request.get("calculator_id", "unknown"))
    try:
        calculator_version = int(request.get("calculator_version", -1))
    except (TypeError, ValueError):
        calculator_version = -1
    result_id = canonical.derive_result_id_unresolvable(request_id, calculator_id, calculator_version, reason)
    return CalculationResult(
        result_id=result_id,
        request_id=request_id,
        calculator_id=calculator_id,
        calculator_version=calculator_version,
        status=RESULT_STATUS_INVALID_INPUT,
        reason=reason,
        output_values=None,
        output_units=None,
        rounding=None,
        warnings=[],
        limitations=[],
        trace_id=None,
        deterministic_input_hash=None,
        deterministic_output_hash=None,
    )


def _unsupported_calculator_result(request: dict, reason: str, warnings: list) -> CalculationResult:
    request_id = str(request["request_id"])
    calculator_id = str(request["calculator_id"])
    calculator_version = int(request["calculator_version"])
    result_id = canonical.derive_result_id_unresolvable(request_id, calculator_id, calculator_version, reason)
    return CalculationResult(
        result_id=result_id,
        request_id=request_id,
        calculator_id=calculator_id,
        calculator_version=calculator_version,
        status=RESULT_STATUS_UNSUPPORTED_CALCULATOR,
        reason=reason,
        output_values=None,
        output_units=None,
        rounding=None,
        warnings=warnings,
        limitations=[],
        trace_id=None,
        deterministic_input_hash=None,
        deterministic_output_hash=None,
    )


def _invalid_input_result(request: dict, reason: str) -> CalculationResult:
    request_id = str(request["request_id"])
    calculator_id = str(request["calculator_id"])
    calculator_version = int(request["calculator_version"])
    result_id = canonical.derive_result_id_unresolvable(request_id, calculator_id, calculator_version, reason)
    return CalculationResult(
        result_id=result_id,
        request_id=request_id,
        calculator_id=calculator_id,
        calculator_version=calculator_version,
        status=RESULT_STATUS_INVALID_INPUT,
        reason=reason,
        output_values=None,
        output_units=None,
        rounding=None,
        warnings=[],
        limitations=[],
        trace_id=None,
        deterministic_input_hash=None,
        deterministic_output_hash=None,
    )


def _failed_closed_result(
    request: dict, reason: str, input_hash: str, warnings: list, limitations: list, root_status: str = None
) -> CalculationResult:
    result_id = canonical.derive_result_id_failed_closed(input_hash)
    return CalculationResult(
        result_id=result_id,
        request_id=str(request["request_id"]),
        calculator_id=str(request["calculator_id"]),
        calculator_version=int(request["calculator_version"]),
        status=RESULT_STATUS_FAILED_CLOSED,
        reason=reason,
        output_values=None,
        output_units=None,
        rounding=None,
        warnings=warnings,
        limitations=limitations,
        trace_id=None,
        deterministic_input_hash=input_hash,
        deterministic_output_hash=None,
        root_status=root_status,
    )


def execute_calculation_request(request: dict) -> Tuple[CalculationResult, Optional[CalculationTrace]]:
    """
    Pure, deterministic. Returns (CalculationResult, CalculationTrace or None).
    Trace is present if and only if status == SUCCESS.
    """
    # --- Step 0: envelope validation ---------------------------------------
    for field in _REQUIRED_ENVELOPE_FIELDS:
        if field not in request or request[field] in (None, ""):
            return _envelope_error_result(request, f"malformed_request_envelope:{field}"), None
    if not isinstance(request["calculator_version"], int):
        return _envelope_error_result(request, "malformed_request_envelope:calculator_version_must_be_integer"), None

    input_values = request.get("input_values", {}) or {}
    input_units = request.get("input_units", {}) or {}
    currency = request.get("currency")
    method = request.get("method")

    # --- Step 1: registry lookup --------------------------------------------
    calc_def = registry.get(request["calculator_id"], request["calculator_version"])
    if calc_def is None:
        reason = (
            "unknown_calculator_version"
            if registry.exists_with_any_version(request["calculator_id"])
            else "unknown_calculator_id"
        )
        return _unsupported_calculator_result(request, reason, []), None
    if calc_def.status == CALCULATOR_STATUS_RETIRED:
        return _unsupported_calculator_result(request, "calculator_retired", calc_def.warnings), None

    # --- Step 2: input normalization -----------------------------------------
    try:
        normalized_method = normalize_method(calc_def, method)
        normalized_currency = validate_currency(currency) if calc_def.requires_currency else currency
        normalized_inputs = normalize_request_inputs(calc_def, input_values, input_units)
    except NormalizationError as exc:
        return _invalid_input_result(request, str(exc)), None

    normalized_dict = normalized_inputs_to_dict(normalized_inputs)
    decimal_map = normalized_inputs_to_decimal_map(normalized_inputs)

    # --- Step 2b: dated cash-flow normalization (LIFE-PROTOTYPE-003) -----------
    context = {}
    extra_hash_content = None
    if calc_def.requires_cash_flows:
        duplicate_date_policy = decimal_map.get("duplicate_date_policy")
        day_count_convention = decimal_map.get("day_count_convention")
        raw_cash_flows = request.get("cash_flows")
        try:
            normalized_cash_flows, duplicate_ops, derived_currency = normalize_cash_flow_list(
                raw_cash_flows, duplicate_date_policy
            )
        except NormalizationError as exc:
            return _invalid_input_result(request, str(exc)), None
        normalized_currency = derived_currency
        context = {
            "cash_flows": normalized_cash_flows,
            "duplicate_date_operations": duplicate_ops,
            "day_count_convention": day_count_convention,
            "duplicate_date_policy": duplicate_date_policy,
            "currency": derived_currency,
        }
        # Two different cash-flow lists MUST hash differently -- fold the
        # fully normalized, canonically-ordered cash-flow content into the
        # input hash. This is the ONLY case where `extra_content` is
        # non-None, so every pre-existing Prototype 002 calculator's hash
        # payload (and therefore hash value) is completely unaffected.
        from life_intelligence_lab.calculators.cash_flow import cash_flow_to_hashable_dict, duplicate_operation_to_dict
        extra_hash_content = {
            "cash_flows": [cash_flow_to_hashable_dict(cf) for cf in normalized_cash_flows],
            "duplicate_date_operations": [duplicate_operation_to_dict(op) for op in duplicate_ops],
        }

    input_hash = canonical.hash_input(
        calculator_id=calc_def.calculator_id,
        calculator_version=calc_def.calculator_version,
        calculation_date=request["calculation_date"],
        currency=normalized_currency,
        method=normalized_method,
        normalized_inputs=normalized_dict,
        extra_content=extra_hash_content,
    )

    # --- Step 3: deterministic calculation -------------------------------------
    compute_fn = _DISPATCH[calc_def.calculator_id]
    try:
        formula_output: FormulaOutput = compute_fn(decimal_map, normalized_method, context)
    except DependencyFailureError as exc:
        return _failed_closed_result(
            request, f"dependency_failure: {exc}", input_hash, calc_def.warnings, calc_def.limitations,
            root_status=ROOT_STATUS_DEPENDENCY_FAILURE,
        ), None
    except DomainError as exc:
        return _failed_closed_result(
            request, str(exc), input_hash, calc_def.warnings, calc_def.limitations, root_status=exc.root_status
        ), None

    # --- Step 4: trace + result assembly ----------------------------------------
    output_after_str = {k: str(v) for k, v in formula_output.output_after_rounding.items()}
    output_before_str = {k: str(v) for k, v in formula_output.output_before_rounding.items()}
    output_hash = canonical.hash_output(output_after_str, calc_def.output_schema)

    trace_id = canonical.derive_trace_id(input_hash, output_hash)
    result_id = canonical.derive_result_id_success(input_hash, output_hash)

    steps = [
        CalculationStep(
            step_number=i + 1,
            description=step.description,
            expression=step.expression,
            unrounded_value=str(step.unrounded_value),
        )
        for i, step in enumerate(formula_output.steps)
    ]

    combined_warnings = list(calc_def.warnings) + list(formula_output.warnings)

    trace = CalculationTrace(
        trace_id=trace_id,
        request_id=request["request_id"],
        calculator_id=calc_def.calculator_id,
        calculator_version=calc_def.calculator_version,
        formula_id=calc_def.formula_id,
        calculation_date=request["calculation_date"],
        currency=normalized_currency,
        method=normalized_method,
        normalized_inputs=normalized_inputs,
        steps=steps,
        output_before_rounding=output_before_str,
        output_after_rounding=output_after_str,
        rounding_applied=formula_output.rounding_applied,
        warnings=combined_warnings,
        implementation_adapter_id=calc_def.implementation_adapter_id,
        implementation_version=RUNTIME_VERSION,
        dependency_versions={"decimal_module": "python_stdlib_decimal", "runtime_version": RUNTIME_VERSION},
        input_hash=input_hash,
        output_hash=output_hash,
        dated_cash_flow_context=formula_output.dated_cash_flow_context,
    )

    result = CalculationResult(
        result_id=result_id,
        request_id=request["request_id"],
        calculator_id=calc_def.calculator_id,
        calculator_version=calc_def.calculator_version,
        status=RESULT_STATUS_SUCCESS,
        reason=None,
        output_values=output_after_str,
        output_units=calc_def.output_schema,
        rounding=formula_output.rounding_applied,
        warnings=combined_warnings,
        limitations=calc_def.limitations,
        trace_id=trace_id,
        deterministic_input_hash=input_hash,
        deterministic_output_hash=output_hash,
        root_status=formula_output.root_status,
        dated_cash_flow_summary=formula_output.dated_cash_flow_summary,
    )

    return result, trace
