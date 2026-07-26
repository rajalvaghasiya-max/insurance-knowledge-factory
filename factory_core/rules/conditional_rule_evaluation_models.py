"""Contracts for downstream conditional-rule evaluation.

This module deliberately defines *inputs and outputs only*. It does not decide
whether a particular insurance clause applies, calculate a claim amount, or
generate customer advice. Domain evaluators introduced later must emit these
contracts so evaluation remains deterministic, reviewable, and evidence-aware.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
from json import dumps
from typing import Any, Mapping


ScenarioScalar = str | int | float | bool | None
ScenarioValue = ScenarioScalar | tuple[ScenarioScalar, ...]


class ApplicabilityStatus(StrEnum):
    """Possible outcomes of evaluating a rule against a scenario."""

    APPLIES = "applies"
    DOES_NOT_APPLY = "does_not_apply"
    INDETERMINATE = "indeterminate"
    NOT_EVALUATED = "not_evaluated"


class PredicateAssessmentStatus(StrEnum):
    """Status for one declared rule predicate."""

    MATCHED = "matched"
    MISMATCHED = "mismatched"
    MISSING_SCENARIO_INPUT = "missing_scenario_input"
    UNSUPPORTED_OPERATOR = "unsupported_operator"
    NOT_EVALUATED = "not_evaluated"


class EffectReadinessStatus(StrEnum):
    """Whether a later financial calculator has enough information to proceed."""

    READY_FOR_CALCULATION = "ready_for_calculation"
    REQUIRES_SCENARIO_SELECTION = "requires_scenario_selection"
    BLOCKED_BY_APPLICABILITY = "blocked_by_applicability"
    BLOCKED_BY_MISSING_INPUT = "blocked_by_missing_input"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True, slots=True)
class EvaluationScenario:
    """A minimal, non-PII scenario contract for rule evaluation.

    ``inputs`` should contain only normalized decision inputs required by a rule
    evaluator (for example, claim_route or pre_approval_status). The scenario
    object intentionally has no claim amount, personal identity, medical record,
    or policy schedule semantics.
    """

    scenario_id: str
    entity_id: str
    inputs: Mapping[str, ScenarioValue]
    as_of_date: str | None = None

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("EvaluationScenario.scenario_id must not be blank.")
        if not self.entity_id.strip():
            raise ValueError("EvaluationScenario.entity_id must not be blank.")
        for key in self.inputs:
            if not isinstance(key, str) or not key.strip():
                raise ValueError("EvaluationScenario.inputs keys must be non-blank strings.")

    def fingerprint(self) -> str:
        """Deterministic fingerprint for traceability without persisting raw inputs."""
        canonical = {
            "scenario_id": self.scenario_id,
            "entity_id": self.entity_id,
            "as_of_date": self.as_of_date,
            "inputs": _canonicalize(self.inputs),
        }
        encoded = dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PredicateAssessment:
    """A record of how one condition/scope predicate was assessed."""

    dimension: str
    operator: str
    expected_value: ScenarioValue
    status: PredicateAssessmentStatus
    scenario_value_present: bool

    def __post_init__(self) -> None:
        if not self.dimension.strip():
            raise ValueError("PredicateAssessment.dimension must not be blank.")
        if not self.operator.strip():
            raise ValueError("PredicateAssessment.operator must not be blank.")
        if self.status is PredicateAssessmentStatus.MISSING_SCENARIO_INPUT and self.scenario_value_present:
            raise ValueError("Missing-input assessment cannot report scenario_value_present=True.")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        if isinstance(self.expected_value, tuple):
            result["expected_value"] = list(self.expected_value)
        return result


@dataclass(frozen=True, slots=True)
class RuleApplicabilityDecision:
    """Contract a future domain evaluator must return before calculation."""

    rule_id: str
    status: ApplicabilityStatus
    predicate_assessments: tuple[PredicateAssessment, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("RuleApplicabilityDecision.rule_id must not be blank.")
        statuses = {item.status for item in self.predicate_assessments}
        if self.status is ApplicabilityStatus.APPLIES and (
            PredicateAssessmentStatus.MISMATCHED in statuses
            or PredicateAssessmentStatus.MISSING_SCENARIO_INPUT in statuses
            or PredicateAssessmentStatus.UNSUPPORTED_OPERATOR in statuses
        ):
            raise ValueError("An applicable decision cannot contain blocking predicate assessments.")
        if self.status is ApplicabilityStatus.INDETERMINATE and not (
            PredicateAssessmentStatus.MISSING_SCENARIO_INPUT in statuses
            or PredicateAssessmentStatus.UNSUPPORTED_OPERATOR in statuses
            or self.reasons
        ):
            raise ValueError("An indeterminate decision requires a missing/unsupported assessment or reason.")
        if self.status is ApplicabilityStatus.DOES_NOT_APPLY and PredicateAssessmentStatus.MISMATCHED not in statuses:
            raise ValueError("A does-not-apply decision requires at least one mismatched predicate.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "predicate_assessments": [item.to_dict() for item in self.predicate_assessments],
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class EffectReadiness:
    """Boundary between rule applicability and later financial calculation.

    This contract states whether calculation may begin. It intentionally does not
    compute money, payable amount, benefit value, or a recommendation.
    """

    rule_id: str
    status: EffectReadinessStatus
    required_inputs: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("EffectReadiness.rule_id must not be blank.")
        if self.status is EffectReadinessStatus.REQUIRES_SCENARIO_SELECTION and not self.required_inputs:
            raise ValueError("Selection-required readiness must name the required input(s).")
        if self.status is EffectReadinessStatus.BLOCKED_BY_MISSING_INPUT and not self.required_inputs:
            raise ValueError("Missing-input readiness must name the required input(s).")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "required_inputs": list(self.required_inputs),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class RuleEvaluationTrace:
    """Evidence-aware, non-PII trace emitted by future evaluators."""

    trace_id: str
    rule_id: str
    source_artifact_path: str
    source_artifact_sha256: str
    scenario_id: str
    scenario_fingerprint: str
    applicability: RuleApplicabilityDecision
    effect_readiness: EffectReadiness
    evaluator_id: str
    evaluator_version: str

    def __post_init__(self) -> None:
        required = {
            "trace_id": self.trace_id,
            "rule_id": self.rule_id,
            "source_artifact_path": self.source_artifact_path,
            "source_artifact_sha256": self.source_artifact_sha256,
            "scenario_id": self.scenario_id,
            "scenario_fingerprint": self.scenario_fingerprint,
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
        }
        for name, value in required.items():
            if not value.strip():
                raise ValueError(f"RuleEvaluationTrace.{name} must not be blank.")
        if self.applicability.rule_id != self.rule_id or self.effect_readiness.rule_id != self.rule_id:
            raise ValueError("Trace rule_id must match applicability and effect-readiness rule IDs.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "rule_id": self.rule_id,
            "source_artifact_path": self.source_artifact_path,
            "source_artifact_sha256": self.source_artifact_sha256,
            "scenario_id": self.scenario_id,
            "scenario_fingerprint": self.scenario_fingerprint,
            "applicability": self.applicability.to_dict(),
            "effect_readiness": self.effect_readiness.to_dict(),
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
        }


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    return value
