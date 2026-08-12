"""Minimal Health benefit-concept seed for MO-028C source pressure.

These concepts are identity/routing assets, not policy limit facts. Comparison-authoritative
label membership is supplied separately through GovernedConceptAlias records.
"""
from __future__ import annotations

from insurance_intelligence.contracts.terminology import (
    CanonicalConceptFamily,
    EvidenceSpan,
    TerminologyPublicationStatus,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
)
from insurance_intelligence.terminology.governed_concept_aliases import (
    GovernedConceptAlias,
    GovernedConceptAliasRegistry,
)


_G0_ARTIFACT = "docs/architecture/MO_028C_G0_AROGYA_SANJEEVANI_BENEFIT_LIMIT_NORMATIVE_INVENTORY.json"


def _benefit(
    concept_id: str,
    canonical_name: str,
    definition: str,
    *,
    ambiguity_group: str | None = None,
) -> CanonicalConceptDefinition:
    return CanonicalConceptDefinition(
        concept=CanonicalConceptFamily(
            concept_family_id=concept_id,
            canonical_name=canonical_name,
            definition=definition,
            domain="health",
            concept_subtype="benefit",
        ),
        concept_type="BENEFIT",
        ambiguity_group=ambiguity_group,
        downstream_topic="benefit_limit",
    )


MO028C_BENEFIT_CONCEPTS = (
    _benefit(
        "health:benefit:cataract",
        "Cataract Treatment",
        "A governed Health benefit concept for cataract treatment or surgery when the product wording identifies cataract as the contractual benefit scope.",
    ),
    _benefit(
        "health:benefit:road_ambulance",
        "Road Ambulance",
        "A governed Health benefit concept for transportation by road ambulance under the applicable product wording.",
        ambiguity_group="health:ambiguity:ambulance_mode",
    ),
    _benefit(
        "health:benefit:air_ambulance",
        "Air Ambulance",
        "A governed Health benefit concept for transportation by air ambulance under the applicable product wording.",
        ambiguity_group="health:ambiguity:ambulance_mode",
    ),
    _benefit(
        "health:benefit:ayush",
        "AYUSH Treatment",
        "A governed Health benefit concept for AYUSH treatment within the contractual scope stated by the product wording.",
    ),
    _benefit(
        "health:benefit:modern_treatment_group",
        "Modern Treatment Group",
        "A governed aggregate Health benefit concept for a source-defined group of modern treatments sharing one contractual limit scope.",
    ),
    _benefit(
        "health:benefit:room_rent",
        "Room Rent",
        "A governed Health benefit concept for eligible hospital room charges or room-category benefit scope.",
    ),
    _benefit(
        "health:benefit:icu",
        "Intensive Care Unit",
        "A governed Health benefit concept for intensive-care-unit charges under the applicable product wording.",
    ),
)


def _evidence(alias_id: str, quoted_text: str) -> tuple[EvidenceSpan, ...]:
    return (
        EvidenceSpan(
            source_id="mo028c_g0_arogya_sanjeevani",
            document_id=_G0_ARTIFACT,
            locator=alias_id,
            quoted_text=quoted_text,
            evidence_id=f"evidence:{alias_id}",
        ),
    )


def _alias(alias_id: str, alias_text: str, concept_id: str) -> GovernedConceptAlias:
    return GovernedConceptAlias(
        alias_id=alias_id,
        alias_text=alias_text,
        concept_id=concept_id,
        evidence_spans=_evidence(alias_id, alias_text),
        review_decision_id="MO_028C_G0_SOURCE_PRESSURE_CERTIFICATION",
        governance_version="mo028c_g1_alias_governance_v1",
        review_status=TerminologyReviewStatus.PUBLISHED,
        publication_status=TerminologyPublicationStatus.AUTHORITATIVE,
        source_scope=_G0_ARTIFACT,
    )


MO028C_GOVERNED_BENEFIT_ALIASES = (
    _alias("mo028c_alias_cataract", "Cataract", "health:benefit:cataract"),
    _alias("mo028c_alias_road_ambulance", "Road Ambulance", "health:benefit:road_ambulance"),
    _alias("mo028c_alias_ayush", "AYUSH", "health:benefit:ayush"),
    _alias(
        "mo028c_alias_modern_treatments",
        "Modern Treatment",
        "health:benefit:modern_treatment_group",
    ),
    _alias("mo028c_alias_room_rent", "Room Rent", "health:benefit:room_rent"),
    _alias("mo028c_alias_icu", "ICU", "health:benefit:icu"),
)


def build_mo028c_benefit_concept_registry() -> CanonicalConceptRegistry:
    return CanonicalConceptRegistry(MO028C_BENEFIT_CONCEPTS)


def build_mo028c_governed_alias_registry() -> GovernedConceptAliasRegistry:
    return GovernedConceptAliasRegistry(
        concept_registry=build_mo028c_benefit_concept_registry(),
        aliases=MO028C_GOVERNED_BENEFIT_ALIASES,
        registry_version="mo028c_benefit_alias_registry_v1",
    )


__all__ = [
    "MO028C_BENEFIT_CONCEPTS",
    "MO028C_GOVERNED_BENEFIT_ALIASES",
    "build_mo028c_benefit_concept_registry",
    "build_mo028c_governed_alias_registry",
]
