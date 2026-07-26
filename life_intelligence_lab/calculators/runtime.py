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
from life_intelligence_lab.calculators.contracts import (
    CALCULATOR_STATUS_RETIRED,
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
from life_intelligence_lab.calculators.formulas import pv as pv_formula
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
_DISPATCH: Dict[str, Callable] = {
    "FV_LUMP_SUM": lambda normalized, method: fv_formula.compute(normalized),
    "PV_LUMP_SUM": lambda normalized, method: pv_formula.compute(normalized),
    "CAGR": lambda normalized, method: cagr_formula.compute(normalized),
    "INFLATION_ADJUSTED_FV": lambda normalized, method: inflation_adjusted.compute(normalized, method),
    "INFLATION_ADJUSTED_FV_APPROX": lambda normalized, method: inflation_adjusted_approx.compute(normalized),
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


def _failed_closed_result(request: dict, reason: str, input_hash: str, warnings: list, limitations: list) -> CalculationResult:
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
    input_hash = canonical.hash_input(
        calculator_id=calc_def.calculator_id,
        calculator_version=calc_def.calculator_version,
        calculation_date=request["calculation_date"],
        currency=normalized_currency,
        method=normalized_method,
        normalized_inputs=normalized_dict,
    )

    # --- Step 3: deterministic calculation -------------------------------------
    decimal_map = normalized_inputs_to_decimal_map(normalized_inputs)
    compute_fn = _DISPATCH[calc_def.calculator_id]
    try:
        formula_output: FormulaOutput = compute_fn(decimal_map, normalized_method)
    except DomainError as exc:
        return _failed_closed_result(request, str(exc), input_hash, calc_def.warnings, calc_def.limitations), None

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
    )

    return result, trace
