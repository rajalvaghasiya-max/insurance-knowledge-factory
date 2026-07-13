"""Health-owned normalization boundary for conditional-rule scenarios.

This adapter turns a constrained set of raw Health scenario labels into the
canonical inputs consumed by the generic applicability evaluator.  It is
intentionally strict: unknown or ambiguous values are rejected rather than
silently guessed.  It does not evaluate rules, calculate money, or produce
customer-facing advice.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from json import dumps
from typing import Any, Mapping

from factory_core.rules.conditional_rule_evaluation_models import EvaluationScenario


class ScenarioNormalizationStatus(StrEnum):
    NORMALIZED = "normalized"
    REJECTED = "rejected"


class ScenarioInputStatus(StrEnum):
    NORMALIZED = "normalized"
    UNKNOWN_DIMENSION = "unknown_dimension"
    UNKNOWN_VALUE = "unknown_value"
    INVALID_TYPE = "invalid_type"


@dataclass(frozen=True, slots=True)
class ScenarioInputNormalization:
    """Non-PII record of how one supplied field was handled."""

    dimension: str
    status: ScenarioInputStatus
    normalized_value: str | None = None
    source_value_fingerprint: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.dimension.strip():
            raise ValueError("ScenarioInputNormalization.dimension must not be blank.")
        if self.status is ScenarioInputStatus.NORMALIZED and self.normalized_value is None:
            raise ValueError("Normalized input must provide normalized_value.")
        if self.status is not ScenarioInputStatus.NORMALIZED and not self.reason:
            raise ValueError("Rejected input must provide a reason.")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "dimension": self.dimension,
            "status": self.status.value,
            "normalized_value": self.normalized_value,
            "source_value_fingerprint": self.source_value_fingerprint,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class HealthScenarioNormalizationResult:
    """Result of strict Health scenario normalization.

    A rejected result intentionally has no EvaluationScenario.  Callers must
    surface or resolve rejected inputs before invoking the generic evaluator.
    Missing dimensions are not an error here: applicability evaluation decides
    whether a particular rule requires them.
    """

    status: ScenarioNormalizationStatus
    scenario: EvaluationScenario | None
    input_assessments: tuple[ScenarioInputNormalization, ...]
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status is ScenarioNormalizationStatus.NORMALIZED and self.scenario is None:
            raise ValueError("A normalized result requires an EvaluationScenario.")
        if self.status is ScenarioNormalizationStatus.REJECTED and self.scenario is not None:
            raise ValueError("A rejected result must not expose an EvaluationScenario.")
        if self.status is ScenarioNormalizationStatus.REJECTED and not self.reasons:
            raise ValueError("A rejected result requires one or more reasons.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "scenario_id": self.scenario.scenario_id if self.scenario else None,
            "entity_id": self.scenario.entity_id if self.scenario else None,
            "normalized_inputs": dict(self.scenario.inputs) if self.scenario else None,
            "input_assessments": [assessment.to_dict() for assessment in self.input_assessments],
            "reasons": list(self.reasons),
        }


# This vocabulary is deliberately small.  New aliases must be added through
# domain review and tests; the normalizer must never use fuzzy matching.
_HEALTH_SCENARIO_VOCABULARY: dict[str, dict[str, str]] = {
    "claim_route": {
        "cashless": "cashless",
        "cash less": "cashless",
        "network cashless": "cashless",
        "reimbursement": "reimbursement",
        "reimburse": "reimbursement",
        "reimbursement claim": "reimbursement",
    },
    "pre_approval_status": {
        "pre approved": "pre_approved",
        "pre approval received": "pre_approved",
        "prior approval received": "pre_approved",
        "not pre approved": "not_pre_approved",
        "not pre-approved": "not_pre_approved",
        "without pre approval": "not_pre_approved",
        "without prior approval": "not_pre_approved",
    },
    "health_cover": {
        "doctor prescribed investigations": "doctor_prescribed_investigations_cover",
        "doctor-prescribed investigations": "doctor_prescribed_investigations_cover",
        "prescribed investigations": "doctor_prescribed_investigations_cover",
        "doctor consultation": "doctor_consultation_cover",
        "consultation": "doctor_consultation_cover",
        "international emergency care": "international_emergency_care",
        "international emergency": "international_emergency_care",
    },
    "health_scope": {
        "international emergency": "international_emergency_care_only",
        "international emergency care": "international_emergency_care_only",
        "international emergency care only": "international_emergency_care_only",
        "voluntary copay option": "voluntary_option",
        "voluntary option": "voluntary_option",
    },
    "cost_share_mode": {
        "voluntary": "voluntary",
        "mandatory": "mandatory",
    },
}


def normalize_health_scenario(
    *,
    scenario_id: str,
    entity_id: str,
    raw_inputs: Mapping[str, Any],
    as_of_date: str | None = None,
) -> HealthScenarioNormalizationResult:
    """Normalize supplied Health decision inputs into an EvaluationScenario.

    Input keys are already expected to be dimensions, rather than arbitrary
    natural-language questions.  Values may use a limited, reviewed alias
    vocabulary.  Unknown dimensions/values and non-string values are rejected.
    """
    if not isinstance(raw_inputs, Mapping):
        raise TypeError("raw_inputs must be a mapping of Health scenario dimensions to values.")

    assessments: list[ScenarioInputNormalization] = []
    normalized: dict[str, str] = {}
    reasons: list[str] = []

    for dimension in sorted(raw_inputs):
        value = raw_inputs[dimension]
        if dimension not in _HEALTH_SCENARIO_VOCABULARY:
            assessments.append(
                ScenarioInputNormalization(
                    dimension=str(dimension),
                    status=ScenarioInputStatus.UNKNOWN_DIMENSION,
                    source_value_fingerprint=_fingerprint(value),
                    reason="This Health scenario dimension is not in the reviewed normalization vocabulary.",
                )
            )
            reasons.append(f"Unsupported scenario dimension: {dimension}")
            continue
        if not isinstance(value, str):
            assessments.append(
                ScenarioInputNormalization(
                    dimension=dimension,
                    status=ScenarioInputStatus.INVALID_TYPE,
                    source_value_fingerprint=_fingerprint(value),
                    reason="Scenario values must be strings at this normalization boundary.",
                )
            )
            reasons.append(f"Invalid value type for scenario dimension: {dimension}")
            continue

        alias = _canonicalize_text(value)
        canonical = _HEALTH_SCENARIO_VOCABULARY[dimension].get(alias)
        if canonical is None:
            assessments.append(
                ScenarioInputNormalization(
                    dimension=dimension,
                    status=ScenarioInputStatus.UNKNOWN_VALUE,
                    source_value_fingerprint=_fingerprint(value),
                    reason="This value is not in the reviewed alias vocabulary for the supplied dimension.",
                )
            )
            reasons.append(f"Unsupported value for scenario dimension: {dimension}")
            continue

        normalized[dimension] = canonical
        assessments.append(
            ScenarioInputNormalization(
                dimension=dimension,
                status=ScenarioInputStatus.NORMALIZED,
                normalized_value=canonical,
                source_value_fingerprint=_fingerprint(value),
            )
        )

    if reasons:
        return HealthScenarioNormalizationResult(
            status=ScenarioNormalizationStatus.REJECTED,
            scenario=None,
            input_assessments=tuple(assessments),
            reasons=tuple(reasons),
        )

    return HealthScenarioNormalizationResult(
        status=ScenarioNormalizationStatus.NORMALIZED,
        scenario=EvaluationScenario(
            scenario_id=scenario_id,
            entity_id=entity_id,
            inputs=normalized,
            as_of_date=as_of_date,
        ),
        input_assessments=tuple(assessments),
    )


def _canonicalize_text(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _fingerprint(value: Any) -> str:
    encoded = dumps(value, sort_keys=True, ensure_ascii=True, default=str, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()
