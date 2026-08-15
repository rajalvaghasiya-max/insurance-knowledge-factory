"""Small primary-source Health definition seed for AFR-N1.

This is intentionally not the full ontology seed. AFR-N1 grows it only as the
primary source for each definition is pinned. Product wording and
marketing/glossary text must not be promoted into this registry merely because
it contains familiar standardized wording.
"""
from __future__ import annotations

from datetime import date

from insurance_intelligence.terminology.standard_definitions import (
    DefinitionEvidenceClass,
    DefinitionSourceReference,
    GovernedStandardDefinition,
    InsuranceCategory,
    StandardDefinitionRegistry,
)


_PED_2020 = GovernedStandardDefinition(
    definition_id="irdai.health.pre_existing_disease.2020.v1",
    canonical_concept_id="health.definition.pre_existing_disease",
    category=InsuranceCategory.HEALTH,
    version="1.0",
    standard_definition=(
        "Pre-existing Disease means any condition, ailment, injury or disease: "
        "a) That is/are diagnosed by a physician within 48 months prior to the effective "
        "date of the policy issued by the insurer or its reinstatement or "
        "b) For which medical advice or treatment was recommended by, or received from, "
        "a physician within 48 months prior to the effective date of the policy issued "
        "by the insurer or its reinstatement."
    ),
    source=DefinitionSourceReference(
        source_id="IRDAI/HLT/REG/CIR/193/07/2020",
        authority="IRDAI",
        locator="Section 1, Chapter I, Clause 33; corrigendum IRDAI/HLT/REG/CIR/225/08/2020",
        source_title="Master Circular on Standardization of Health Insurance Products",
    ),
    evidence_class=DefinitionEvidenceClass.PRIMARY_REGULATORY_SOURCE,
    effective_from=date(2020, 10, 1),
    effective_to=date(2024, 3, 31),
    aliases=("pre-existing disease", "pre existing disease", "PED"),
)


_PED_2024 = GovernedStandardDefinition(
    definition_id="irdai.health.pre_existing_disease.2024.v2",
    canonical_concept_id="health.definition.pre_existing_disease",
    category=InsuranceCategory.HEALTH,
    version="2.0",
    standard_definition=(
        "Pre-existing disease (PED) normally means any condition, ailment, injury or "
        "disease that is/are diagnosed by a physician not more than 36 months prior to "
        "the date of commencement of the policy issued by the insurer; or for which "
        "medical advice or treatment was recommended by, or received from, a physician, "
        "not more than 36 months prior to the date of commencement of the policy."
    ),
    source=DefinitionSourceReference(
        source_id="IRDAI/HLT/CIR/PRO/84/5/2024",
        authority="IRDAI",
        locator="IRDAI Health Department current guidance; Master Circular on Health Insurance Business dated 29-05-2024",
        source_title="Master Circular on Health Insurance Business 2024",
    ),
    evidence_class=DefinitionEvidenceClass.PRIMARY_REGULATORY_SOURCE,
    effective_from=date(2024, 4, 1),
    effective_to=None,
    aliases=("pre-existing disease", "pre existing disease", "PED"),
)


_ROOM_RENT_2020 = GovernedStandardDefinition(
    definition_id="irdai.health.room_rent.2020.v1",
    canonical_concept_id="health.definition.room_rent",
    category=InsuranceCategory.HEALTH,
    version="1.0",
    standard_definition=(
        "Room Rent means the amount charged by a Hospital towards Room and Boarding "
        "expenses and shall include the associated medical expenses."
    ),
    source=DefinitionSourceReference(
        source_id="IRDAI/HLT/REG/CIR/193/07/2020",
        authority="IRDAI",
        locator="Chapter I — Standard Definitions and Standard Nomenclature, Room Rent",
        source_title="Master Circular on Standardization of Health Insurance Products",
    ),
    evidence_class=DefinitionEvidenceClass.PRIMARY_REGULATORY_SOURCE,
    effective_from=date(2020, 10, 1),
    effective_to=date(2024, 3, 31),
    aliases=("room rent", "room and boarding expenses"),
)


_CUMULATIVE_BONUS_2024 = GovernedStandardDefinition(
    definition_id="irdai.health.cumulative_bonus.2024.v1",
    canonical_concept_id="health.definition.cumulative_bonus",
    category=InsuranceCategory.HEALTH,
    version="1.0",
    standard_definition=(
        "Addition in the Sum Insured without an associated increase in premium."
    ),
    source=DefinitionSourceReference(
        source_id="IRDAI_HEALTH_DEPT_FAQ_CURRENT",
        authority="IRDAI",
        locator="Health Department FAQ 30 — No Claim Bonus; Cumulative Bonus form",
        source_title="IRDAI Health Department FAQs",
    ),
    evidence_class=DefinitionEvidenceClass.PRIMARY_REGULATOR_GUIDANCE_SOURCE,
    effective_from=date(2024, 5, 29),
    effective_to=None,
    aliases=("cumulative bonus", "health cumulative bonus"),
    not_synonyms=("motor no claim bonus", "motor NCB"),
)


_COPAYMENT_2024 = GovernedStandardDefinition(
    definition_id="irdai.health.copayment.2024.v1",
    canonical_concept_id="health.definition.copayment",
    category=InsuranceCategory.HEALTH,
    version="1.0",
    standard_definition=(
        "Co-payment is a specified amount / percentage of the admissible claim amount "
        "to be paid by policyholder / insured."
    ),
    source=DefinitionSourceReference(
        source_id="IRDAI_HEALTH_DEPT_FAQ_CURRENT",
        authority="IRDAI",
        locator="Health Department FAQ 12 — What is co-payment?",
        source_title="IRDAI Health Department FAQs",
    ),
    evidence_class=DefinitionEvidenceClass.PRIMARY_REGULATOR_GUIDANCE_SOURCE,
    effective_from=date(2024, 5, 29),
    effective_to=None,
    aliases=("co-payment", "copayment", "co payment"),
)


def build_health_regulatory_definition_registry() -> StandardDefinitionRegistry:
    registry = StandardDefinitionRegistry()
    registry.register(_PED_2020)
    registry.register(_PED_2024)
    registry.register(_ROOM_RENT_2020)
    registry.register(_CUMULATIVE_BONUS_2024)
    registry.register(_COPAYMENT_2024)
    return registry


__all__ = ["build_health_regulatory_definition_registry"]
