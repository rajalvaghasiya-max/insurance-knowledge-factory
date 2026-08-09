"""Governed qualitative assessment policies for MO-026B.

Policies define how one insurance dimension may be classified on its own terms.
They are versioned governance artifacts. They do not aggregate dimensions, assign
cross-benefit weights, rank products, infer suitability, or recommend products.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import AssessmentBand
from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus


class AssessmentPolicyError(ValueError):
    """Raised when a governed assessment policy violates an invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentPolicyError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise AssessmentPolicyError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(value, f"{field_name}[]") for value in values)
    if not allow_empty and not cleaned:
        raise AssessmentPolicyError(f"{field_name} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise AssessmentPolicyError(f"{field_name} must not contain duplicates")
    return cleaned


class CriterionOperator(str, Enum):
    EQUALS = "EQUALS"
    IN = "IN"
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


@dataclass(frozen=True)
class AssessmentCriterion:
    """One deterministic mechanic-level condition used by an assessment rule."""

    mechanic_id: str
    operator: CriterionOperator
    expected_value: object | None = None
    rationale: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mechanic_id", _required_text(self.mechanic_id, "mechanic_id"))
        if not isinstance(self.operator, CriterionOperator):
            raise AssessmentPolicyError("operator must be a CriterionOperator")
        object.__setattr__(self, "rationale", _required_text(self.rationale, "rationale"))
        if self.operator in {CriterionOperator.EQUALS, CriterionOperator.IN} and self.expected_value is None:
            raise AssessmentPolicyError(f"{self.operator.value} criterion requires expected_value")
        if self.operator in {CriterionOperator.PRESENT, CriterionOperator.ABSENT} and self.expected_value is not None:
            raise AssessmentPolicyError(f"{self.operator.value} criterion cannot carry expected_value")
        if self.operator is CriterionOperator.IN:
            if not isinstance(self.expected_value, tuple) or not self.expected_value:
                raise AssessmentPolicyError("IN criterion expected_value must be a non-empty tuple")


@dataclass(frozen=True)
class AssessmentBandRule:
    """A deterministic set of criteria that yields one qualitative assessment band."""

    rule_id: str
    band: AssessmentBand
    criteria: tuple[AssessmentCriterion, ...]
    explanation_template: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_text(self.rule_id, "rule_id"))
        if not isinstance(self.band, AssessmentBand):
            raise AssessmentPolicyError("band must be an AssessmentBand")
        if not isinstance(self.criteria, tuple) or not self.criteria:
            raise AssessmentPolicyError("criteria must be a non-empty tuple")
        if not all(isinstance(item, AssessmentCriterion) for item in self.criteria):
            raise AssessmentPolicyError("criteria must contain AssessmentCriterion values")
        object.__setattr__(
            self,
            "explanation_template",
            _required_text(self.explanation_template, "explanation_template"),
        )


@dataclass(frozen=True)
class BenefitAssessmentPolicy:
    """Governed policy for assessing one canonical insurance dimension."""

    policy_id: str
    policy_version: str
    dimension_id: str
    required_mechanic_ids: tuple[str, ...]
    band_rules: tuple[AssessmentBandRule, ...]
    not_scorable_reason: str
    governance_basis: str
    review_status: ReviewStatus
    publication_status: PublicationStatus
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "policy_id",
            "policy_version",
            "dimension_id",
            "not_scorable_reason",
            "governance_basis",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "required_mechanic_ids",
            _text_tuple(self.required_mechanic_ids, "required_mechanic_ids", allow_empty=False),
        )
        if not isinstance(self.band_rules, tuple) or not self.band_rules:
            raise AssessmentPolicyError("band_rules must be a non-empty tuple")
        if not all(isinstance(item, AssessmentBandRule) for item in self.band_rules):
            raise AssessmentPolicyError("band_rules must contain AssessmentBandRule values")
        rule_ids = tuple(item.rule_id for item in self.band_rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise AssessmentPolicyError("band_rules must not contain duplicate rule ids")
        bands = tuple(item.band for item in self.band_rules)
        if len(bands) != len(set(bands)):
            raise AssessmentPolicyError("band_rules must not contain duplicate assessment bands")
        known_required = set(self.required_mechanic_ids)
        for rule in self.band_rules:
            unknown = {item.mechanic_id for item in rule.criteria} - known_required
            if unknown:
                raise AssessmentPolicyError(
                    f"band rule references mechanics not declared by policy: {sorted(unknown)}"
                )
        if not isinstance(self.review_status, ReviewStatus):
            raise AssessmentPolicyError("review_status must be a ReviewStatus")
        if not isinstance(self.publication_status, PublicationStatus):
            raise AssessmentPolicyError("publication_status must be a PublicationStatus")
        if not isinstance(self.effective_from, date):
            raise AssessmentPolicyError("effective_from must be a date")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise AssessmentPolicyError("effective_to must be a date or None")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise AssessmentPolicyError("effective_to cannot be before effective_from")

    @property
    def is_governed_for_use(self) -> bool:
        return self.review_status is ReviewStatus.APPROVED and self.publication_status is PublicationStatus.PUBLISHED

    def is_active(self, as_of: date) -> bool:
        if not isinstance(as_of, date):
            raise AssessmentPolicyError("as_of must be a date")
        return self.effective_from <= as_of and (self.effective_to is None or as_of <= self.effective_to)


__all__ = [
    "AssessmentBandRule",
    "AssessmentCriterion",
    "AssessmentPolicyError",
    "BenefitAssessmentPolicy",
    "CriterionOperator",
]
