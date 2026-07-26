"""
life_intelligence_lab.calculators.serialization
==================================================

Converts the contract dataclasses to/from fixed-field-order plain dicts,
for JSON I/O and for canonical hashing. Kept as a single, deliberate
boundary so field ordering is defined once (in `contracts.py`'s
*_FIELD_ORDER constants) and never re-derived ad hoc elsewhere.
"""

from __future__ import annotations

from typing import Optional

from life_intelligence_lab.calculators.contracts import (
    CALCULATION_RESULT_FIELD_ORDER,
    CALCULATION_STEP_FIELD_ORDER,
    CALCULATION_TRACE_FIELD_ORDER,
    NORMALIZED_INPUT_FIELD_ORDER,
    CalculationResult,
    CalculationStep,
    CalculationTrace,
    NormalizedInput,
)


def normalized_input_to_dict(ni: NormalizedInput) -> dict:
    full = {
        "field_name": ni.field_name,
        "original_value": ni.original_value,
        "original_unit": ni.original_unit,
        "normalized_value": ni.normalized_value,
        "normalized_unit": ni.normalized_unit,
    }
    return {k: full[k] for k in NORMALIZED_INPUT_FIELD_ORDER}


def normalized_input_from_dict(d: dict) -> NormalizedInput:
    return NormalizedInput(**d)


def step_to_dict(step: CalculationStep) -> dict:
    full = {
        "step_number": step.step_number,
        "description": step.description,
        "expression": step.expression,
        "unrounded_value": step.unrounded_value,
    }
    return {k: full[k] for k in CALCULATION_STEP_FIELD_ORDER}


def step_from_dict(d: dict) -> CalculationStep:
    return CalculationStep(**d)


def trace_to_dict(trace: CalculationTrace) -> dict:
    full = {
        "trace_id": trace.trace_id,
        "request_id": trace.request_id,
        "calculator_id": trace.calculator_id,
        "calculator_version": trace.calculator_version,
        "formula_id": trace.formula_id,
        "calculation_date": trace.calculation_date,
        "currency": trace.currency,
        "method": trace.method,
        "normalized_inputs": [normalized_input_to_dict(ni) for ni in trace.normalized_inputs],
        "steps": [step_to_dict(s) for s in trace.steps],
        "output_before_rounding": trace.output_before_rounding,
        "output_after_rounding": trace.output_after_rounding,
        "rounding_applied": trace.rounding_applied,
        "warnings": trace.warnings,
        "implementation_adapter_id": trace.implementation_adapter_id,
        "implementation_version": trace.implementation_version,
        "dependency_versions": trace.dependency_versions,
        "input_hash": trace.input_hash,
        "output_hash": trace.output_hash,
    }
    return {k: full[k] for k in CALCULATION_TRACE_FIELD_ORDER}


def trace_from_dict(d: dict) -> CalculationTrace:
    return CalculationTrace(
        trace_id=d["trace_id"],
        request_id=d["request_id"],
        calculator_id=d["calculator_id"],
        calculator_version=d["calculator_version"],
        formula_id=d["formula_id"],
        calculation_date=d["calculation_date"],
        currency=d["currency"],
        method=d["method"],
        normalized_inputs=[normalized_input_from_dict(ni) for ni in d["normalized_inputs"]],
        steps=[step_from_dict(s) for s in d["steps"]],
        output_before_rounding=d["output_before_rounding"],
        output_after_rounding=d["output_after_rounding"],
        rounding_applied=d["rounding_applied"],
        warnings=d["warnings"],
        implementation_adapter_id=d["implementation_adapter_id"],
        implementation_version=d["implementation_version"],
        dependency_versions=d["dependency_versions"],
        input_hash=d["input_hash"],
        output_hash=d["output_hash"],
    )


def result_to_dict(result: CalculationResult) -> dict:
    full = {
        "result_id": result.result_id,
        "request_id": result.request_id,
        "calculator_id": result.calculator_id,
        "calculator_version": result.calculator_version,
        "status": result.status,
        "reason": result.reason,
        "output_values": result.output_values,
        "output_units": result.output_units,
        "rounding": result.rounding,
        "warnings": result.warnings,
        "limitations": result.limitations,
        "trace_id": result.trace_id,
        "deterministic_input_hash": result.deterministic_input_hash,
        "deterministic_output_hash": result.deterministic_output_hash,
    }
    return {k: full[k] for k in CALCULATION_RESULT_FIELD_ORDER}


def result_from_dict(d: dict) -> CalculationResult:
    return CalculationResult(**d)
