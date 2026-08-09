"""Deterministic per-benefit assessment engine for MO-026B.

The engine applies one governed assessment policy to one governed product-benefit
implementation. It produces an education-first BenefitAssessment only. It does
not aggregate benefits, rank products, infer suitability, or recommend a plan.
"""
from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentStatus,
    BenefitAssessment,
)
from insurance_intelligence.benefits.assessment_policies import (
    AssessmentBandRule,
    AssessmentCriterion,
    AssessmentPolicyError,
    BenefitAssessmentPolicy,
    CriterionOperator,
)
from insurance_intelligence.benefits.assessment_taxonomy import AssessmentDimensionDefinition
from insurance_intelligence.benefits.contracts import BenefitMechanic, ProductBenefitImplementation


class BenefitAssessmentEngineError(ValueError):
    """Raised when deterministic assessment inputs are invalid or incompatible."""


def _stable_assessment_id(implementation_id: str, policy_id: str, policy_version: str) -> str:
    payload = "\x1f".join((implementation_id, policy_id, policy_version))
    return f"assessment-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _mechanics_by_id(implementation: ProductBenefitImplementation) -> dict[str, BenefitMechanic]:
    return {item.dimension_id: item for item in implementation.mechanics}


def _criterion_matches(criterion: AssessmentCriterion, mechanic: BenefitMechanic | None) -> bool:
    if criterion.operator is CriterionOperator.PRESENT:
        return mechanic is not None
    if criterion.operator is CriterionOperator.ABSENT:
        return mechanic is None
    if mechanic is None:
        return False
    if criterion.operator is CriterionOperator.EQUALS:
        return mechanic.value == criterion.expected_value
    if criterion.operator is CriterionOperator.IN:
        return mechanic.value in criterion.expected_value
    raise AssessmentPolicyError(f"unsupported criterion operator: {criterion.operator}")


def _rule_matches(rule: AssessmentBandRule, mechanics: dict[str, BenefitMechanic]) -> bool:
    return all(_criterion_matches(item, mechanics.get(item.mechanic_id)) for item in rule.criteria)


def _evidence_ids(mechanics: tuple[BenefitMechanic, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            evidence_id
            for mechanic in mechanics
            for evidence_id in mechanic.evidence_reference_ids
        )
    )


def assess_product_benefit(
    *,
    implementation: ProductBenefitImplementation,
    dimension: AssessmentDimensionDefinition,
    policy: BenefitAssessmentPolicy,
) -> BenefitAssessment:
    """Apply a governed qualitative policy to one product-benefit implementation."""

    if not isinstance(implementation, ProductBenefitImplementation):
        raise BenefitAssessmentEngineError(
            "implementation must be a ProductBenefitImplementation"
        )
    if not isinstance(dimension, AssessmentDimensionDefinition):
        raise BenefitAssessmentEngineError(
            "dimension must be an AssessmentDimensionDefinition"
        )
    if not isinstance(policy, BenefitAssessmentPolicy):
        raise BenefitAssessmentEngineError("policy must be a BenefitAssessmentPolicy")
    if dimension.dimension_id != policy.dimension_id:
        raise BenefitAssessmentEngineError("dimension and policy dimension_id must match")
    if not implementation.is_governed_for_use:
        raise BenefitAssessmentEngineError(
            "implementation must be approved and published for governed assessment"
        )
    if not policy.is_governed_for_use:
        raise BenefitAssessmentEngineError(
            "assessment policy must be approved and published for governed use"
        )

    mechanics = _mechanics_by_id(implementation)
    missing_required = tuple(
        mechanic_id
        for mechanic_id in policy.required_mechanic_ids
        if mechanic_id not in mechanics
    )
    available_required = tuple(
        mechanics[mechanic_id]
        for mechanic_id in policy.required_mechanic_ids
        if mechanic_id in mechanics
    )
    evidence_ids = _evidence_ids(available_required)
    source_ids = tuple(item.dimension_id for item in available_required)
    assessment_id = _stable_assessment_id(
        implementation.implementation_id,
        policy.policy_id,
        policy.policy_version,
    )

    if missing_required:
        limitation = (
            f"{policy.not_scorable_reason} Missing required mechanics: "
            + ", ".join(missing_required)
        )
        return BenefitAssessment(
            assessment_id=assessment_id,
            implementation_id=implementation.implementation_id,
            concept_id=implementation.concept_id,
            dimension_id=dimension.dimension_id,
            decision_role=dimension.decision_role,
            status=AssessmentStatus.NOT_SCORABLE,
            assessment_band=None,
            assessment_policy_id=policy.policy_id,
            assessment_policy_version=policy.policy_version,
            summary="Assessment unavailable on the governed mechanics currently available.",
            practical_meaning=(
                "PolicyScna will not classify this benefit until the required governed mechanics are available."
            ),
            source_mechanic_ids=source_ids or policy.required_mechanic_ids,
            evidence_reference_ids=evidence_ids or tuple(
                dict.fromkeys(
                    evidence_id
                    for mechanic in implementation.mechanics
                    for evidence_id in mechanic.evidence_reference_ids
                )
            ),
            limitations=(limitation,),
        )

    matched_rule = next(
        (rule for rule in policy.band_rules if _rule_matches(rule, mechanics)),
        None,
    )
    if matched_rule is None:
        return BenefitAssessment(
            assessment_id=assessment_id,
            implementation_id=implementation.implementation_id,
            concept_id=implementation.concept_id,
            dimension_id=dimension.dimension_id,
            decision_role=dimension.decision_role,
            status=AssessmentStatus.NOT_SCORABLE,
            assessment_band=None,
            assessment_policy_id=policy.policy_id,
            assessment_policy_version=policy.policy_version,
            summary="No governed assessment band matches the available mechanics.",
            practical_meaning=(
                "The benefit facts are preserved, but PolicyScna will not force them into an unsupported qualitative band."
            ),
            source_mechanic_ids=source_ids,
            evidence_reference_ids=evidence_ids,
            limitations=(
                "No published assessment rule matches the governed mechanic combination.",
            ),
        )

    limitations = tuple(implementation.limitations)
    status = (
        AssessmentStatus.ASSESSED_WITH_LIMITATIONS
        if limitations
        else AssessmentStatus.ASSESSED
    )
    return BenefitAssessment(
        assessment_id=assessment_id,
        implementation_id=implementation.implementation_id,
        concept_id=implementation.concept_id,
        dimension_id=dimension.dimension_id,
        decision_role=dimension.decision_role,
        status=status,
        assessment_band=matched_rule.band,
        assessment_policy_id=policy.policy_id,
        assessment_policy_version=policy.policy_version,
        summary=matched_rule.explanation_template,
        practical_meaning=(
            "This is an intrinsic assessment of the restoration mechanics only. It is not an overall product rating, "
            "customer suitability conclusion, or recommendation."
        ),
        source_mechanic_ids=source_ids,
        evidence_reference_ids=evidence_ids,
        limitations=limitations,
    )


__all__ = [
    "BenefitAssessmentEngineError",
    "assess_product_benefit",
]
