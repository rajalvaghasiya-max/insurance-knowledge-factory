"""Minimal certified-candidate Health semantic backbone for the pre-G11 increment.

This is intentionally narrow. It gives existing governed capabilities immutable,
category-namespaced identities before the hostile third-product exercise. It does
not attempt to become a comprehensive insurance glossary.
"""
from __future__ import annotations

from insurance_intelligence.generic_knowledge.assessment_policy import (
    AssessmentPolicy,
    AssessmentPolicyRegistry,
)
from insurance_intelligence.generic_knowledge.semantic_registry import (
    ApplicabilitySchema,
    CanonicalConcept,
    CanonicalConceptRegistry,
    InsuranceCategory,
)


HEALTH_ONTOLOGY_RELEASE = "health_semantics_2026_08_pre_g11"


WAITING_PERIOD_APPLICABILITY = ApplicabilitySchema(
    schema_id="health.waiting_periods.applicability",
    version="1",
    common_axes=(
        "product_reference",
        "policy_version",
        "variant",
        "sum_insured_band",
        "optional_cover_state",
        "effective_range",
    ),
)

COPAYMENT_APPLICABILITY = ApplicabilitySchema(
    schema_id="health.copayment.applicability",
    version="1",
    common_axes=(
        "product_reference",
        "policy_version",
        "variant",
        "zone",
        "sum_insured_band",
        "effective_range",
    ),
)

ROOM_RENT_APPLICABILITY = ApplicabilitySchema(
    schema_id="health.room_rent_restriction.applicability",
    version="1",
    common_axes=(
        "product_reference",
        "policy_version",
        "variant",
        "zone",
        "sum_insured_band",
        "effective_range",
    ),
)

RESTORATION_APPLICABILITY = ApplicabilitySchema(
    schema_id="health.restoration.applicability",
    version="1",
    common_axes=(
        "product_reference",
        "policy_version",
        "variant",
        "sum_insured_band",
        "effective_range",
    ),
)


HEALTH_CANONICAL_CONCEPTS = CanonicalConceptRegistry(
    (
        CanonicalConcept(
            canonical_id="health.waiting_periods",
            category=InsuranceCategory.HEALTH,
            concept_version="1",
            ontology_release=HEALTH_ONTOLOGY_RELEASE,
            fact_schema_id="waiting_periods_v1",
            applicability_schema=WAITING_PERIOD_APPLICABILITY,
            definition_reference_id="semantic-definition:health.waiting_periods:v1",
            gloss="Rules that delay coverage for defined illnesses, conditions, procedures, or pre-existing diseases subject to governed scope and exceptions.",
            aliases=("waiting_periods", "waiting period", "waiting periods"),
        ),
        CanonicalConcept(
            canonical_id="health.copayment",
            category=InsuranceCategory.HEALTH,
            concept_version="1",
            ontology_release=HEALTH_ONTOLOGY_RELEASE,
            fact_schema_id="copayment_v1",
            applicability_schema=COPAYMENT_APPLICABILITY,
            definition_reference_id="semantic-definition:health.copayment:v1",
            gloss="A governed cost-sharing mechanic under which the insured bears a defined part of an admissible claim when its applicability conditions are met.",
            aliases=("copayment", "co-payment", "co pay", "copay"),
        ),
        CanonicalConcept(
            canonical_id="health.room_rent_restriction",
            category=InsuranceCategory.HEALTH,
            concept_version="1",
            ontology_release=HEALTH_ONTOLOGY_RELEASE,
            fact_schema_id="room_rent_restriction_v1",
            applicability_schema=ROOM_RENT_APPLICABILITY,
            definition_reference_id="semantic-definition:health.room_rent_restriction:v1",
            gloss="A governed restriction on eligible hospital room or ICU accommodation; any downstream claim consequence is represented separately rather than implied by this concept alone.",
            aliases=("room_rent_restriction", "room rent", "room-rent restriction"),
        ),
        CanonicalConcept(
            canonical_id="health.restoration",
            category=InsuranceCategory.HEALTH,
            concept_version="1",
            ontology_release=HEALTH_ONTOLOGY_RELEASE,
            fact_schema_id="restoration_v1",
            applicability_schema=RESTORATION_APPLICABILITY,
            definition_reference_id="semantic-definition:health.restoration:v1",
            gloss="A governed benefit mechanic that restores or replenishes coverage subject to product-defined triggers, scope, reuse, and exclusions.",
            aliases=("restoration", "sum insured restoration"),
            negative_aliases=("recharge", "reinstatement"),
        ),
    )
)


HEALTH_ASSESSMENT_POLICIES = AssessmentPolicyRegistry(
    (
        AssessmentPolicy(
            policy_id="assessment:health.copayment:v1",
            version="1",
            canonical_concept_id="health.copayment",
            mandatory_consideration=True,
            suppression_allowed=False,
            warning_required=True,
            rationale="Cost-sharing can materially change the insured's out-of-pocket exposure and must not disappear from product-centric assessment.",
        ),
        AssessmentPolicy(
            policy_id="assessment:health.room_rent_restriction:v1",
            version="1",
            canonical_concept_id="health.room_rent_restriction",
            mandatory_consideration=True,
            suppression_allowed=False,
            warning_required=True,
            rationale="Room eligibility restrictions can materially affect claim economics and must remain visible without assuming a consequence not established by evidence.",
        ),
    )
)


__all__ = [
    "HEALTH_ASSESSMENT_POLICIES",
    "HEALTH_CANONICAL_CONCEPTS",
    "HEALTH_ONTOLOGY_RELEASE",
]
