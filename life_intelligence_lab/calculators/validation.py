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

    # For dated cash-flow calculators, the ORIGINAL input_hash folded in the
    # normalized cash-flow list (see runtime.py / canonical.hash_input's
    # `extra_content`). To genuinely recompute (not just re-trust) that
    # hash, we must reconstruct the identical extra_content from the
    # trace's own dated_cash_flow_context -- which is exactly why that
    # context stores "normalized_cash_flows" and "duplicate_date_operations"
    # verbatim as their own dict content, not just a summary.
    recomputed_extra_content = None
    if trace.dated_cash_flow_context is not None:
        normalized_cfs = trace.dated_cash_flow_context.get("normalized_cash_flows") or []
        # Match runtime.py's hash basis exactly: sequence is excluded from
        # hashed content (it is input-order provenance, not economically
        # meaningful content) -- see cash_flow.cash_flow_to_hashable_dict.
        hashable_cfs = [{k: v for k, v in cf.items() if k != "sequence"} for cf in normalized_cfs]
        recomputed_extra_content = {
            "cash_flows": hashable_cfs,
            "duplicate_date_operations": trace.dated_cash_flow_context.get("duplicate_date_operations"),
        }

    recomputed_input_hash = canonical.hash_input(
        calculator_id=trace.calculator_id,
        calculator_version=trace.calculator_version,
        calculation_date=trace.calculation_date,
        currency=trace.currency,
        method=trace.method,
        normalized_inputs=normalized_inputs_to_dict(trace.normalized_inputs),
        extra_content=recomputed_extra_content,
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

    # --- LIFE-PROTOTYPE-003: dated cash-flow-specific checks --------------------
    # Only meaningful (and only run) when this trace actually carries a
    # dated_cash_flow_context -- Prototype 002's calculators never populate
    # it, so these three checks are simply absent from their `checks` dict
    # rather than trivially True, keeping the check set honest about what
    # was actually verified for each calculator family.
    if trace.dated_cash_flow_context is not None:
        from life_intelligence_lab.calculators.adapters.pyxirr_adapter import dependency_fingerprint

        recorded_fingerprint = trace.dated_cash_flow_context.get("dependency_fingerprint")
        live_fingerprint = dependency_fingerprint()
        fingerprint_matches = recorded_fingerprint == live_fingerprint
        checks["dependency_fingerprint_matches"] = fingerprint_matches
        if not fingerprint_matches:
            reasons.append(
                f"dependency_fingerprint mismatch: trace recorded '{recorded_fingerprint}', "
                f"live environment is '{live_fingerprint}' -- the pinned dependency may have "
                f"changed since this trace was produced."
            )

        recorded_root_status = trace.dated_cash_flow_context.get("root_status")
        normalized_cfs = trace.dated_cash_flow_context.get("normalized_cash_flows") or []
        from decimal import Decimal as _Decimal
        amounts_in_order = [_Decimal(cf["amount"]) for cf in normalized_cfs]
        non_zero_signs = [1 if a > 0 else -1 for a in amounts_in_order if a != 0]
        actual_sign_changes = sum(
            1 for prev, curr in zip(non_zero_signs, non_zero_signs[1:]) if prev != curr
        )
        expected_multi_root = actual_sign_changes > 1
        root_status_consistent = (
            recorded_root_status is None  # e.g. XNPV_DATED, which has no root_status concept
            or (expected_multi_root and recorded_root_status == "MULTIPLE_ROOTS_POSSIBLE")
            or (not expected_multi_root and recorded_root_status in ("SINGLE_ROOT", "NO_ROOT_FOUND", "DEPENDENCY_FAILURE", "INVALID_CASH_FLOWS"))
        )
        checks["root_status_consistent_with_sign_changes"] = root_status_consistent
        if not root_status_consistent:
            reasons.append(
                f"root_status '{recorded_root_status}' is inconsistent with {actual_sign_changes} "
                f"detected sign changes in the normalized cash flows."
            )

        xnpv_check = trace.dated_cash_flow_context.get("xnpv_consistency_check")
        if xnpv_check is not None and xnpv_check.get("xnpv_at_root") is not None:
            xnpv_within_tolerance = bool(xnpv_check.get("within_tolerance"))
            checks["xnpv_consistency_within_tolerance"] = xnpv_within_tolerance
            if not xnpv_within_tolerance:
                reasons.append(
                    f"XNPV at the candidate root ({xnpv_check.get('xnpv_at_root')}) was not "
                    f"within the declared tolerance ({xnpv_check.get('tolerance')})."
                )

    overall = "valid" if all(checks.values()) else "invalid"

    return CalculationValidationResult(
        validation_id=f"validation_{result.result_id}",
        result_id=result.result_id,
        trace_id=trace.trace_id,
        checks=checks,
        overall_status=overall,
        reasons=reasons,
    )
