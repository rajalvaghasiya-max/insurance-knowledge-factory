"""Small primary-source Motor definition seed for AFR-N1.C.

The seed is intentionally narrow. It exists to pressure the category boundary
against Health terminology, not to start Motor product onboarding.
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


_MOTOR_NCB_CURRENT = GovernedStandardDefinition(
    definition_id="irdai.motor.no_claim_bonus.current.v1",
    canonical_concept_id="motor.definition.no_claim_bonus",
    category=InsuranceCategory.MOTOR,
    version="1.0",
    standard_definition=(
        "No Claim Bonus (NCB) is the benefit accrued to an insured for NIL claims during "
        "the previous policy period."
    ),
    source=DefinitionSourceReference(
        source_id="IRDAI_POLICYHOLDER_MOTOR_INSURANCE_CURRENT",
        authority="IRDAI",
        locator=(
            "Motor Insurance FAQ — What is No Claim Bonus?; current guidance also "
            "describes the benefit against Own Damage premium rather than Liability premium"
        ),
        source_title="IRDAI Motor Insurance - Policy Holder",
    ),
    evidence_class=DefinitionEvidenceClass.PRIMARY_REGULATOR_GUIDANCE_SOURCE,
    # This is a conservative certification floor for the current 2024+ general-insurance
    # framework, not a claim that Motor NCB originated on this date.
    effective_from=date(2024, 6, 11),
    effective_to=None,
    aliases=("no claim bonus", "NCB", "motor no claim bonus", "motor NCB"),
    not_synonyms=("cumulative bonus", "health cumulative bonus"),
)


def build_motor_regulatory_definition_registry() -> StandardDefinitionRegistry:
    registry = StandardDefinitionRegistry()
    registry.register(_MOTOR_NCB_CURRENT)
    return registry


__all__ = ["build_motor_regulatory_definition_registry"]
