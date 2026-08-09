"""Shared product-centric assessment policy for MO-026/MO-027 consumers.

This layer is intentionally outside the canonical ontology and outside personalized
decision support. It governs analytical safeguards such as mandatory consideration,
suppression rules, and required interaction-aware assessment keyed by canonical IDs.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.generic_knowledge.contracts import GenericKnowledgeContractError


class AssessmentPolicyError(GenericKnowledgeContractError):
    """Raised when an assessment policy violates an invariant."""


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentPolicyError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise AssessmentPolicyError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(value, field_name) for value in values)
    if len(cleaned) != len(set(cleaned)):
        raise AssessmentPolicyError(f"{field_name} must not contain duplicates")
    return cleaned


@dataclass(frozen=True)
class AssessmentPolicy:
    policy_id: str
    version: str
    canonical_concept_id: str
    mandatory_consideration: bool
    suppression_allowed: bool
    required_interaction_concept_ids: tuple[str, ...] = ()
    warning_required: bool = False
    rationale: str = "Governed assessment safeguard."

    def __post_init__(self) -> None:
        for field_name in ("policy_id", "version", "canonical_concept_id", "rationale"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if type(self.mandatory_consideration) is not bool:
            raise AssessmentPolicyError("mandatory_consideration must be boolean")
        if type(self.suppression_allowed) is not bool:
            raise AssessmentPolicyError("suppression_allowed must be boolean")
        if type(self.warning_required) is not bool:
            raise AssessmentPolicyError("warning_required must be boolean")
        interactions = _text_tuple(
            self.required_interaction_concept_ids,
            "required_interaction_concept_ids",
        )
        if self.canonical_concept_id in interactions:
            raise AssessmentPolicyError("a concept cannot require an interaction with itself")
        if self.mandatory_consideration and self.suppression_allowed:
            raise AssessmentPolicyError(
                "mandatory_consideration cannot allow suppression"
            )
        object.__setattr__(self, "required_interaction_concept_ids", interactions)


class AssessmentPolicyRegistry:
    """Immutable versioned lookup keyed by canonical concept id."""

    def __init__(self, policies: tuple[AssessmentPolicy, ...]) -> None:
        if not isinstance(policies, tuple):
            raise AssessmentPolicyError("policies must be a tuple")
        if not all(type(item) is AssessmentPolicy for item in policies):
            raise AssessmentPolicyError("policies must contain exact AssessmentPolicy values")
        ids = tuple(item.policy_id for item in policies)
        if len(ids) != len(set(ids)):
            raise AssessmentPolicyError("policy_id values must be unique")
        concepts = tuple(item.canonical_concept_id for item in policies)
        if len(concepts) != len(set(concepts)):
            raise AssessmentPolicyError(
                "only one active assessment policy per canonical concept is allowed"
            )
        self._by_concept = {item.canonical_concept_id: item for item in policies}

    def for_concept(self, canonical_concept_id: str) -> AssessmentPolicy | None:
        return self._by_concept.get(_text(canonical_concept_id, "canonical_concept_id"))

    def must_surface(self, canonical_concept_id: str) -> bool:
        policy = self.for_concept(canonical_concept_id)
        return bool(policy and policy.mandatory_consideration and not policy.suppression_allowed)


__all__ = [
    "AssessmentPolicy",
    "AssessmentPolicyError",
    "AssessmentPolicyRegistry",
]
