"""Deterministic cross-component coherence validation for governed explanations.

This layer validates relationships between already-canonical semantic components.
It never interprets prose and never uses provider confidence as a substitute for
logical consistency.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.contracts.rule_family_registry import RuleFamilyBinding
from insurance_intelligence.contracts.semantic_fidelity import (
    ExplanationSemanticContract,
    SemanticComparisonStatus,
    SemanticFidelityReport,
    SemanticKind,
)


class ExplanationCoherenceStatus(str, Enum):
    COHERENT = "COHERENT"
    INCOHERENT = "INCOHERENT"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class ExplanationCoherenceCheck:
    check_id: str
    passed: bool
    failure_code: str | None = None


@dataclass(frozen=True)
class ExplanationCoherenceResult:
    status: ExplanationCoherenceStatus
    checks: tuple[ExplanationCoherenceCheck, ...]
    failure_codes: tuple[str, ...]


def _attributes(component) -> dict[str, object]:
    return {item.name: item.value for item in component.attributes}


def _component_for_role(
    contract: ExplanationSemanticContract,
    binding: RuleFamilyBinding,
    role: str,
):
    component_id = binding.component_id_for(role)
    if component_id is None:
        return None
    return next((item for item in contract.components if item.component_id == component_id), None)


def _matched(report: SemanticFidelityReport, component_id: str | None) -> bool:
    if component_id is None:
        return False
    comparison = next(
        (item for item in report.comparisons if item.component_id == component_id),
        None,
    )
    return comparison is not None and comparison.status is SemanticComparisonStatus.MATCHED


def _numeric(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _conditions_overlap(left_operator: object, left_value: object, right_operator: object, right_value: object) -> bool | None:
    """Return whether simple one-dimensional threshold predicates overlap.

    None means the predicate form is unsupported and coherence proof is incomplete.
    """
    lv = _numeric(left_value)
    rv = _numeric(right_value)
    if lv is None or rv is None or not isinstance(left_operator, str) or not isinstance(right_operator, str):
        return None
    if left_operator == ">=" and right_operator == "<":
        return rv > lv
    if left_operator == ">" and right_operator == "<=":
        return rv > lv
    if left_operator == "<" and right_operator == ">=":
        return lv > rv
    if left_operator == "<=" and right_operator == ">":
        return lv > rv
    return None


def validate_explanation_coherence(
    contract: ExplanationSemanticContract,
    binding: RuleFamilyBinding,
    report: SemanticFidelityReport,
) -> ExplanationCoherenceResult:
    """Validate deterministic coherence for a governed conditional-copayment rule.

    The first version intentionally supports only the proven CONDITIONAL_COPAYMENT
    family. Unknown families fail closed as INCOMPLETE rather than being guessed.
    """
    checks: list[ExplanationCoherenceCheck] = []
    failures: set[str] = set()

    if binding.family_id != contract.rule_family or binding.contract_id != contract.contract_id:
        return ExplanationCoherenceResult(
            status=ExplanationCoherenceStatus.INCOMPLETE,
            checks=(ExplanationCoherenceCheck("binding_identity", False, "COHERENCE_BINDING_MISMATCH"),),
            failure_codes=("COHERENCE_BINDING_MISMATCH",),
        )
    if contract.rule_family != "CONDITIONAL_COPAYMENT":
        return ExplanationCoherenceResult(
            status=ExplanationCoherenceStatus.INCOMPLETE,
            checks=(ExplanationCoherenceCheck("supported_rule_family", False, "COHERENCE_RULE_FAMILY_UNSUPPORTED"),),
            failure_codes=("COHERENCE_RULE_FAMILY_UNSUPPORTED",),
        )

    role_components = {
        role: _component_for_role(contract, binding, role)
        for role in ("trigger", "effect", "exception", "scope")
    }
    required_roles = ("trigger", "effect", "scope")
    missing_roles = tuple(role for role in required_roles if role_components[role] is None)
    if missing_roles:
        failures.add("COHERENCE_PROOF_INCOMPLETE")
        checks.append(ExplanationCoherenceCheck("required_roles_present", False, "COHERENCE_PROOF_INCOMPLETE"))
    else:
        checks.append(ExplanationCoherenceCheck("required_roles_present", True))

    expected_kinds = {
        "trigger": SemanticKind.TRIGGER,
        "effect": SemanticKind.EFFECT,
        "exception": SemanticKind.EXCEPTION,
        "scope": SemanticKind.APPLICABILITY_SCOPE,
    }
    kind_ok = all(
        component is None or component.kind is expected_kinds[role]
        for role, component in role_components.items()
    )
    if not kind_ok:
        failures.add("ROLE_KIND_MISMATCH")
    checks.append(ExplanationCoherenceCheck("role_kind_consistency", kind_ok, None if kind_ok else "ROLE_KIND_MISMATCH"))

    fidelity_ok = all(
        _matched(report, role_components[role].component_id if role_components[role] is not None else None)
        for role in required_roles
    )
    exception = role_components["exception"]
    if exception is not None:
        fidelity_ok = fidelity_ok and _matched(report, exception.component_id)
    if not fidelity_ok:
        failures.add("COHERENCE_PROOF_INCOMPLETE")
    checks.append(ExplanationCoherenceCheck("component_fidelity_complete", fidelity_ok, None if fidelity_ok else "COHERENCE_PROOF_INCOMPLETE"))

    effect = role_components["effect"]
    effect_ok = False
    if effect is not None:
        attrs = _attributes(effect)
        percentage = _numeric(attrs.get("percentage"))
        effect_ok = attrs.get("effect_type") == "copayment" and percentage is not None and 0 < percentage <= 100
    if not effect_ok:
        failures.add("EFFECT_SEMANTICS_INVALID")
    checks.append(ExplanationCoherenceCheck("effect_semantics", effect_ok, None if effect_ok else "EFFECT_SEMANTICS_INVALID"))

    scope = role_components["scope"]
    scope_ok = False
    if scope is not None:
        attrs = _attributes(scope)
        mode = attrs.get("mode")
        sections = attrs.get("sections")
        scope_ok = mode == "exact_set" and isinstance(sections, tuple) and bool(sections)
    if not scope_ok:
        failures.add("SCOPE_BINDING_MISMATCH")
    checks.append(ExplanationCoherenceCheck("scope_effect_binding", scope_ok, None if scope_ok else "SCOPE_BINDING_MISMATCH"))

    trigger = role_components["trigger"]
    trigger_exception_ok = True
    trigger_exception_complete = True
    if trigger is not None and exception is not None:
        trigger_attrs = _attributes(trigger)
        exception_attrs = _attributes(exception)
        overlap = _conditions_overlap(
            trigger_attrs.get("operator"),
            trigger_attrs.get("value"),
            exception_attrs.get("age_operator"),
            exception_attrs.get("age_value"),
        )
        if overlap is None:
            trigger_exception_complete = False
            trigger_exception_ok = False
            failures.add("COHERENCE_PROOF_INCOMPLETE")
        elif overlap:
            trigger_exception_ok = False
            failures.add("TRIGGER_EXCEPTION_CONTRADICTION")
        if exception_attrs.get("logical_operator") != "AND":
            trigger_exception_ok = False
            failures.add("EXCEPTION_LOGIC_MISMATCH")
        if exception_attrs.get("continuous_renewal") is not True or exception_attrs.get("policy_break") is not False:
            trigger_exception_ok = False
            failures.add("EXCEPTION_SEMANTICS_INVALID")
    checks.append(
        ExplanationCoherenceCheck(
            "trigger_exception_consistency",
            trigger_exception_ok,
            None if trigger_exception_ok else (
                "COHERENCE_PROOF_INCOMPLETE" if not trigger_exception_complete else "TRIGGER_EXCEPTION_CONTRADICTION"
            ),
        )
    )

    if "COHERENCE_PROOF_INCOMPLETE" in failures or "COHERENCE_BINDING_MISMATCH" in failures:
        status = ExplanationCoherenceStatus.INCOMPLETE
    elif failures:
        status = ExplanationCoherenceStatus.INCOHERENT
    else:
        status = ExplanationCoherenceStatus.COHERENT
    return ExplanationCoherenceResult(
        status=status,
        checks=tuple(checks),
        failure_codes=tuple(sorted(failures)),
    )


__all__ = [
    "ExplanationCoherenceCheck",
    "ExplanationCoherenceResult",
    "ExplanationCoherenceStatus",
    "validate_explanation_coherence",
]
