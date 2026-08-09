"""Governed projection from deterministic reasoning findings into MO-026 assessments.

This bridge preserves a governed conditional-rule finding as structured assessment
input without converting it into a ProductBenefitImplementation. It is intentionally
narrow: only supported, evidence-linked conditional findings with explicit trigger
semantics may cross the boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from insurance_intelligence.contracts.reasoning import Finding


class ConditionAssessmentProjectionError(ValueError):
    """Raised when a reasoning finding cannot safely enter benefit assessment."""


def _required_text(value: str | None, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConditionAssessmentProjectionError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_text(value, "optional_text")


@dataclass(frozen=True)
class GovernedConditionAssessmentProjection:
    projection_id: str
    finding_id: str
    dimension_id: str
    percentage: float
    trigger: str
    exception: str | None
    applicability_scope: str | None
    evidence_ids: tuple[str, ...]
    rule_id: str
    rule_version: str
    confidence: float

    def __post_init__(self) -> None:
        for field_name in ("projection_id", "finding_id", "dimension_id", "trigger", "rule_id", "rule_version"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        object.__setattr__(self, "exception", _optional_text(self.exception))
        object.__setattr__(self, "applicability_scope", _optional_text(self.applicability_scope))
        if not isinstance(self.percentage, (int, float)) or isinstance(self.percentage, bool):
            raise ConditionAssessmentProjectionError("percentage must be numeric")
        numeric = float(self.percentage)
        if not 0 <= numeric <= 100:
            raise ConditionAssessmentProjectionError("percentage must be between 0 and 100")
        object.__setattr__(self, "percentage", numeric)
        if not isinstance(self.evidence_ids, tuple) or not self.evidence_ids:
            raise ConditionAssessmentProjectionError("evidence_ids must be a non-empty tuple")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ConditionAssessmentProjectionError("evidence_ids must be unique")
        if not all(isinstance(item, str) and item.strip() for item in self.evidence_ids):
            raise ConditionAssessmentProjectionError("evidence_ids must contain non-empty text")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise ConditionAssessmentProjectionError("confidence must be numeric")
        if not 0 <= float(self.confidence) <= 1:
            raise ConditionAssessmentProjectionError("confidence must be between 0 and 1")


_PERCENTAGE = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%")


def project_conditional_copayment_finding(
    finding: Finding,
) -> GovernedConditionAssessmentProjection:
    """Project one governed conditional copayment finding into assessment mechanics."""

    if type(finding) is not Finding:
        raise ConditionAssessmentProjectionError("finding must be the exact governed Finding type")
    if finding.finding_type != "CLAIM_COST_SHARING":
        raise ConditionAssessmentProjectionError("finding_type must be CLAIM_COST_SHARING")
    if finding.predicate != "must_bear":
        raise ConditionAssessmentProjectionError("copayment finding predicate must be must_bear")
    if finding.finding_status != "CONDITIONAL":
        raise ConditionAssessmentProjectionError("copayment finding must have CONDITIONAL status")
    if finding.derivation_type != "CONDITIONAL_DERIVATION":
        raise ConditionAssessmentProjectionError("copayment finding must use CONDITIONAL_DERIVATION")
    if finding.rule_id != "conditional_copayment_obligation_v1":
        raise ConditionAssessmentProjectionError("unsupported conditional copayment rule")
    trigger = _required_text(finding.trigger, "finding.trigger")
    if not finding.evidence_ids:
        raise ConditionAssessmentProjectionError("finding must preserve evidence_ids")
    match = _PERCENTAGE.search(finding.object_or_effect)
    if not match:
        raise ConditionAssessmentProjectionError("copayment finding must contain a documented percentage")
    percentage = float(match.group(1))
    projection_id = f"condition_assessment:{finding.finding_id}:copayment"
    return GovernedConditionAssessmentProjection(
        projection_id=projection_id,
        finding_id=finding.finding_id,
        dimension_id="copayment",
        percentage=percentage,
        trigger=trigger,
        exception=finding.exception,
        applicability_scope=finding.applicability_scope,
        evidence_ids=finding.evidence_ids,
        rule_id=finding.rule_id,
        rule_version=finding.rule_version,
        confidence=finding.confidence,
    )


__all__ = [
    "ConditionAssessmentProjectionError",
    "GovernedConditionAssessmentProjection",
    "project_conditional_copayment_finding",
]
