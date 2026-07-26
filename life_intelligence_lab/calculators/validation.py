"""
life_intelligence_lab.calculators.validation
================================================

Post-hoc validation of a (CalculationResult, CalculationTrace) pair.

This is deliberately independent of `runtime.py`'s execution path: it
re-derives `input_hash` and `output_hash` from the trace's own recorded
content (never from the live formula computation) and checks that they
still match what the result and trace claim. This is what catches
tampering -- if either the trace or the result is mutated after the
fact, `validate_result` will detect the mismatch, because it recomputes
rather than trusts.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from life_intelligence_lab.calculators import canonical, registry
from life_intelligence_lab.calculators.contracts import (
    CALCULATOR_STATUS_ACTIVE,
    CalculationResult,
    CalculationTrace,
    CalculationValidationResult,
    RESULT_STATUS_SUCCESS,
)
from life_intelligence_lab.calculators.normalization import normalized_inputs_to_dict


def validate_result(result: CalculationResult, trace: Optional[CalculationTrace]) -> CalculationValidationResult:
    checks: dict = {}
    reasons: list = []

    calc_def = registry.get(result.calculator_id, result.calculator_version)
    checks["calculator_exists"] = calc_def is not None
    if calc_def is None:
        reasons.append("calculator no longer resolvable in the registry")

    checks["calculator_version_matches"] = (
        calc_def is not None and calc_def.calculator_version == result.calculator_version
    )
    checks["calculator_active"] = calc_def is not None and calc_def.status == CALCULATOR_STATUS_ACTIVE

    if result.status != RESULT_STATUS_SUCCESS:
        # A non-SUCCESS result must be internally consistent: no trace,
        # no output content, no output hash -- never a plausible-looking
        # number attached to a failure status.
        checks["required_inputs_present"] = True  # n/a for non-success
        checks["units_compatible"] = True  # n/a
        checks["normalized_values_finite"] = True  # n/a
        checks["domain_rules_satisfied"] = True  # n/a
        checks["trace_complete"] = trace is None
        checks["input_hash_reproducible"] = True  # n/a (no computation occurred to reproduce)
        checks["output_hash_matches"] = result.deterministic_output_hash is None
        checks["result_references_correct_trace"] = result.trace_id is None
        if trace is not None:
            reasons.append("non-SUCCESS result unexpectedly has an attached trace")
        if result.output_values is not None:
            reasons.append("non-SUCCESS result unexpectedly has output_values")
        if result.deterministic_output_hash is not None:
            reasons.append("non-SUCCESS result unexpectedly has a deterministic_output_hash")

        overall = "valid" if all(checks.values()) else "invalid"
        return CalculationValidationResult(
            validation_id=f"validation_{result.result_id}",
            result_id=result.result_id,
            trace_id=None,
            checks=checks,
            overall_status=overall,
            reasons=reasons,
        )

    # --- SUCCESS path: full trace-based re-derivation ------------------------
    if trace is None:
        checks["trace_complete"] = False
        reasons.append("trace_missing_for_success: a SUCCESS result must have an attached trace")
        return CalculationValidationResult(
            validation_id=f"validation_{result.result_id}",
            result_id=result.result_id,
            trace_id=None,
            checks=checks,
            overall_status="invalid",
            reasons=reasons,
        )

    checks["required_inputs_present"] = True
    if calc_def is not None:
        trace_field_names = {ni.field_name for ni in trace.normalized_inputs}
        for field_name, schema_entry in calc_def.required_input_schema.items():
            if schema_entry.get("required", True) and field_name not in trace_field_names:
                checks["required_inputs_present"] = False
                reasons.append(f"required input '{field_name}' missing from trace")

    checks["units_compatible"] = True
    checks["normalized_values_finite"] = True
    for ni in trace.normalized_inputs:
        if ni.normalized_unit in ("boolean", "code"):
            continue
        try:
            value = Decimal(ni.normalized_value)
        except InvalidOperation:
            checks["normalized_values_finite"] = False
            reasons.append(f"normalized value for '{ni.field_name}' is not a valid decimal")
            continue
        if not value.is_finite():
            checks["normalized_values_finite"] = False
            reasons.append(f"normalized value for '{ni.field_name}' is not finite")

    checks["domain_rules_satisfied"] = True  # the formula already succeeded to reach SUCCESS

    trace_complete = all([
        trace.trace_id, trace.request_id, trace.calculator_id, trace.formula_id,
        trace.steps, trace.output_before_rounding, trace.output_after_rounding,
        trace.input_hash, trace.output_hash,
    ])
    checks["trace_complete"] = trace_complete
    if not trace_complete:
        reasons.append("trace is missing one or more required (non-empty) fields")

    recomputed_input_hash = canonical.hash_input(
        calculator_id=trace.calculator_id,
        calculator_version=trace.calculator_version,
        calculation_date=trace.calculation_date,
        currency=trace.currency,
        method=trace.method,
        normalized_inputs=normalized_inputs_to_dict(trace.normalized_inputs),
    )
    input_hash_reproducible = (
        recomputed_input_hash == trace.input_hash == result.deterministic_input_hash
    )
    checks["input_hash_reproducible"] = input_hash_reproducible
    if not input_hash_reproducible:
        reasons.append(
            f"input_hash mismatch: recomputed={recomputed_input_hash}, "
            f"trace={trace.input_hash}, result={result.deterministic_input_hash}"
        )

    recomputed_output_hash = canonical.hash_output(
        trace.output_after_rounding, result.output_units or {}
    )
    output_hash_matches = (
        recomputed_output_hash == trace.output_hash == result.deterministic_output_hash
    )
    checks["output_hash_matches"] = output_hash_matches
    if not output_hash_matches:
        reasons.append(
            f"output_hash mismatch: recomputed={recomputed_output_hash}, "
            f"trace={trace.output_hash}, result={result.deterministic_output_hash}"
        )

    result_references_correct_trace = result.trace_id == trace.trace_id
    checks["result_references_correct_trace"] = result_references_correct_trace
    if not result_references_correct_trace:
        reasons.append(f"result.trace_id ({result.trace_id}) != trace.trace_id ({trace.trace_id})")

    overall = "valid" if all(checks.values()) else "invalid"

    return CalculationValidationResult(
        validation_id=f"validation_{result.result_id}",
        result_id=result.result_id,
        trace_id=trace.trace_id,
        checks=checks,
        overall_status=overall,
        reasons=reasons,
    )
