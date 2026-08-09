"""Governed circumstance-to-product relevance contracts for MO-027D.

This module is deliberately narrower than a suitability or needs-analysis engine.
It may connect a confirmed customer circumstance to the applicability or material
relevance of an already-governed product dimension only when that relationship is
itself represented by an approved, published, versioned rule with traceable evidence.
It must not tell a customer what they should value, assign product verdicts, or
aggregate across dimensions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus


class CircumstanceRelevanceError(ValueError):
    """Raised when circumstance relevance governance invariants are violated."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CircumstanceRelevanceError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise CircumstanceRelevanceError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(value, f"{field_name}[]") for value in values)
    if not allow_empty and not cleaned:
        raise CircumstanceRelevanceError(f"{field_name} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise CircumstanceRelevanceError(f"{field_name} must not contain duplicates")
    return cleaned


class CustomerFactProvenance(str, Enum):
    DECLARED = "DECLARED"
    INFERRED = "INFERRED"
    CONFIRMED = "CONFIRMED"


class CircumstanceOperator(str, Enum):
    EQUALS = "EQUALS"
    IN = "IN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class RelevanceClaimType(str, Enum):
    PRODUCT_APPLICABILITY = "PRODUCT_APPLICABILITY"
    DIMENSION_MATERIALITY = "DIMENSION_MATERIALITY"
    NEEDS_ANALYSIS = "NEEDS_ANALYSIS"


class RelevanceEffect(str, Enum):
    CONDITION_POTENTIALLY_APPLICABLE = "CONDITION_POTENTIALLY_APPLICABLE"
    CONDITION_NOT_APPLICABLE = "CONDITION_NOT_APPLICABLE"
    DIMENSION_MATERIALLY_APPLICABLE = "DIMENSION_MATERIALLY_APPLICABLE"
    DIMENSION_NOT_APPLICABLE = "DIMENSION_NOT_APPLICABLE"


class RelevanceRuleBasis(str, Enum):
    PRODUCT_POLICY_MECHANIC = "PRODUCT_POLICY_MECHANIC"
    POLICY_DEFINITION_AND_CLAUSE = "POLICY_DEFINITION_AND_CLAUSE"
    REGULATORY_RULE = "REGULATORY_RULE"
    GOVERNED_DOMAIN_EVIDENCE = "GOVERNED_DOMAIN_EVIDENCE"


@dataclass(frozen=True)
class CustomerCircumstanceFact:
    fact_id: str
    subject_reference: str
    circumstance_id: str
    value: object
    provenance: CustomerFactProvenance
    raw_statement: str

    def __post_init__(self) -> None:
        for field_name in ("fact_id", "subject_reference", "circumstance_id", "raw_statement"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if not isinstance(self.provenance, CustomerFactProvenance):
            raise CircumstanceRelevanceError("provenance must be a CustomerFactProvenance")

    @property
    def is_confirmed_for_deterministic_use(self) -> bool:
        return self.provenance in {
            CustomerFactProvenance.DECLARED,
            CustomerFactProvenance.CONFIRMED,
        }


@dataclass(frozen=True)
class CircumstanceRelevanceRule:
    rule_id: str
    rule_version: str
    circumstance_id: str
    operator: CircumstanceOperator
    expected_value: object | None
    target_dimension_id: str
    claim_type: RelevanceClaimType
    effect: RelevanceEffect
    basis: RelevanceRuleBasis
    rationale: str
    evidence_reference_ids: tuple[str, ...]
    review_status: ReviewStatus
    publication_status: PublicationStatus
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "rule_id",
            "rule_version",
            "circumstance_id",
            "target_dimension_id",
            "rationale",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if not isinstance(self.operator, CircumstanceOperator):
            raise CircumstanceRelevanceError("operator must be a CircumstanceOperator")
        if not isinstance(self.claim_type, RelevanceClaimType):
            raise CircumstanceRelevanceError("claim_type must be a RelevanceClaimType")
        if self.claim_type is RelevanceClaimType.NEEDS_ANALYSIS:
            raise CircumstanceRelevanceError(
                "NEEDS_ANALYSIS rules are outside the default MO-027D path and must not be published here"
            )
        if not isinstance(self.effect, RelevanceEffect):
            raise CircumstanceRelevanceError("effect must be a RelevanceEffect")
        if not isinstance(self.basis, RelevanceRuleBasis):
            raise CircumstanceRelevanceError("basis must be a RelevanceRuleBasis")
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(self.evidence_reference_ids, "evidence_reference_ids", allow_empty=False),
        )
        if self.operator in {
            CircumstanceOperator.EQUALS,
            CircumstanceOperator.IN,
            CircumstanceOperator.GREATER_THAN_OR_EQUAL,
            CircumstanceOperator.LESS_THAN_OR_EQUAL,
        } and self.expected_value is None:
            raise CircumstanceRelevanceError(f"{self.operator.value} requires expected_value")
        if self.operator in {CircumstanceOperator.PRESENT, CircumstanceOperator.ABSENT} and self.expected_value is not None:
            raise CircumstanceRelevanceError(f"{self.operator.value} cannot carry expected_value")
        if self.operator is CircumstanceOperator.IN and (
            not isinstance(self.expected_value, tuple) or not self.expected_value
        ):
            raise CircumstanceRelevanceError("IN expected_value must be a non-empty tuple")
        if not isinstance(self.review_status, ReviewStatus):
            raise CircumstanceRelevanceError("review_status must be a ReviewStatus")
        if not isinstance(self.publication_status, PublicationStatus):
            raise CircumstanceRelevanceError("publication_status must be a PublicationStatus")
        if not isinstance(self.effective_from, date):
            raise CircumstanceRelevanceError("effective_from must be a date")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise CircumstanceRelevanceError("effective_to must be a date or None")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise CircumstanceRelevanceError("effective_to cannot be before effective_from")

    @property
    def is_governed_for_use(self) -> bool:
        return self.review_status is ReviewStatus.APPROVED and self.publication_status is PublicationStatus.PUBLISHED

    def is_active(self, as_of: date) -> bool:
        if not isinstance(as_of, date):
            raise CircumstanceRelevanceError("as_of must be a date")
        return self.effective_from <= as_of and (self.effective_to is None or as_of <= self.effective_to)


@dataclass(frozen=True)
class CircumstanceRelevanceFinding:
    finding_id: str
    fact_id: str
    rule_id: str
    rule_version: str
    target_dimension_id: str
    claim_type: RelevanceClaimType
    effect: RelevanceEffect
    rationale: str
    evidence_reference_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "finding_id",
            "fact_id",
            "rule_id",
            "rule_version",
            "target_dimension_id",
            "rationale",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if not isinstance(self.claim_type, RelevanceClaimType):
            raise CircumstanceRelevanceError("claim_type must be a RelevanceClaimType")
        if not isinstance(self.effect, RelevanceEffect):
            raise CircumstanceRelevanceError("effect must be a RelevanceEffect")
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(self.evidence_reference_ids, "evidence_reference_ids", allow_empty=False),
        )


def _matches(fact: CustomerCircumstanceFact, rule: CircumstanceRelevanceRule) -> bool:
    value = fact.value
    expected = rule.expected_value
    if rule.operator is CircumstanceOperator.EQUALS:
        return value == expected
    if rule.operator is CircumstanceOperator.IN:
        assert isinstance(expected, tuple)
        return value in expected
    if rule.operator is CircumstanceOperator.PRESENT:
        return value is not None
    if rule.operator is CircumstanceOperator.ABSENT:
        return value is None
    if rule.operator is CircumstanceOperator.GREATER_THAN_OR_EQUAL:
        try:
            return value >= expected
        except TypeError as exc:
            raise CircumstanceRelevanceError("fact value cannot be compared using GREATER_THAN_OR_EQUAL") from exc
    if rule.operator is CircumstanceOperator.LESS_THAN_OR_EQUAL:
        try:
            return value <= expected
        except TypeError as exc:
            raise CircumstanceRelevanceError("fact value cannot be compared using LESS_THAN_OR_EQUAL") from exc
    raise CircumstanceRelevanceError("unsupported circumstance operator")


def evaluate_circumstance_relevance(
    *,
    fact: CustomerCircumstanceFact,
    rule: CircumstanceRelevanceRule,
    as_of: date,
) -> CircumstanceRelevanceFinding | None:
    """Evaluate one governed circumstance rule without performing needs analysis."""

    if type(fact) is not CustomerCircumstanceFact:
        raise CircumstanceRelevanceError("fact must be the exact CustomerCircumstanceFact type")
    if type(rule) is not CircumstanceRelevanceRule:
        raise CircumstanceRelevanceError("rule must be the exact CircumstanceRelevanceRule type")
    if not fact.is_confirmed_for_deterministic_use:
        raise CircumstanceRelevanceError(
            "inferred circumstance facts must be confirmed before deterministic relevance evaluation"
        )
    if not rule.is_governed_for_use:
        raise CircumstanceRelevanceError("rule must be approved and published for governed use")
    if not rule.is_active(as_of):
        raise CircumstanceRelevanceError("rule is not active for the requested date")
    if fact.circumstance_id != rule.circumstance_id:
        raise CircumstanceRelevanceError("fact and rule circumstance ids must match")
    if not _matches(fact, rule):
        return None
    return CircumstanceRelevanceFinding(
        finding_id=f"circumstance_relevance:{fact.fact_id}:{rule.rule_id}:{rule.rule_version}",
        fact_id=fact.fact_id,
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        target_dimension_id=rule.target_dimension_id,
        claim_type=rule.claim_type,
        effect=rule.effect,
        rationale=rule.rationale,
        evidence_reference_ids=rule.evidence_reference_ids,
    )


__all__ = [
    "CircumstanceOperator",
    "CircumstanceRelevanceError",
    "CircumstanceRelevanceFinding",
    "CircumstanceRelevanceRule",
    "CustomerCircumstanceFact",
    "CustomerFactProvenance",
    "RelevanceClaimType",
    "RelevanceEffect",
    "RelevanceRuleBasis",
    "evaluate_circumstance_relevance",
]
