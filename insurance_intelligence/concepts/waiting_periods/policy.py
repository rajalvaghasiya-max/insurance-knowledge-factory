"""Reusable waiting-period concept policy for MO-028B.G5.

This module contains domain semantics for the waiting-period concept, never insurer/product
identity.  It supplies the G4 high-recall relevance envelope and declares the semantic effects
that later mappers must account for.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.generic_knowledge.contracts import (
    NormativeUnitKind,
    RelationshipType,
)
from insurance_intelligence.generic_knowledge.relevance_inventory import (
    ConceptRelevanceEnvelope,
    InventoryRule,
)


class WaitingPeriodSemanticEffect(str, Enum):
    DURATION = "DURATION"
    START_BASIS = "START_BASIS"
    SCOPE = "SCOPE"
    EXCEPTION = "EXCEPTION"
    CONTINUITY = "CONTINUITY"
    PORTABILITY = "PORTABILITY"
    SUM_INSURED_ENHANCEMENT = "SUM_INSURED_ENHANCEMENT"
    WAIVER = "WAIVER"
    REDUCTION = "REDUCTION"
    APPLICABILITY = "APPLICABILITY"
    OPTIONAL_COVER_INTERACTION = "OPTIONAL_COVER_INTERACTION"
    BENEFIT_SCOPED_OVERRIDE = "BENEFIT_SCOPED_OVERRIDE"
    CROSS_CONCEPT_RELATIONSHIP = "CROSS_CONCEPT_RELATIONSHIP"
    RENEWAL_OR_REINSTATEMENT_EFFECT = "RENEWAL_OR_REINSTATEMENT_EFFECT"
    EFFECTIVE_DATE_OR_VERSION = "EFFECTIVE_DATE_OR_VERSION"
    OTHER_NORMATIVE_EFFECT = "OTHER_NORMATIVE_EFFECT"


@dataclass(frozen=True)
class WaitingPeriodConceptPolicy:
    concept: str
    policy_version: str
    envelope: ConceptRelevanceEnvelope
    allowed_relationship_types: tuple[RelationshipType, ...]
    semantic_effects: tuple[WaitingPeriodSemanticEffect, ...]


_ALL_SOURCE_CLASSES = (
    "POLICY_WORDING",
    "CUSTOMER_INFORMATION_SHEET",
    "PROSPECTUS",
    "BROCHURE",
    "WEBPAGE",
    "MARKETING",
    "REGULATORY_OVERLAY",
)


def _rule(
    rule_id: str,
    anchors: tuple[str, ...],
    kind: NormativeUnitKind,
    *effects: WaitingPeriodSemanticEffect,
) -> InventoryRule:
    return InventoryRule(
        rule_id=rule_id,
        anchors=anchors,
        kind=kind,
        materially_affects=tuple(effect.value for effect in effects),
        allowed_source_classes=_ALL_SOURCE_CLASSES,
    )


def waiting_period_concept_policy() -> WaitingPeriodConceptPolicy:
    """Return the reusable waiting-period concept policy.

    Anchors are deliberately broad and high-recall.  They select candidate normative content;
    they do not decide product facts or publication values.
    """
    rules = (
        _rule(
            "wp_named_waiting_period",
            ("waiting period", "waiting periods"),
            NormativeUnitKind.CONDITION,
            WaitingPeriodSemanticEffect.DURATION,
            WaitingPeriodSemanticEffect.START_BASIS,
            WaitingPeriodSemanticEffect.SCOPE,
            WaitingPeriodSemanticEffect.APPLICABILITY,
        ),
        _rule(
            "wp_pre_existing_disease",
            ("pre-existing disease", "pre existing disease", "code-excl01", "code- excl01"),
            NormativeUnitKind.EXCLUSION,
            WaitingPeriodSemanticEffect.DURATION,
            WaitingPeriodSemanticEffect.SCOPE,
            WaitingPeriodSemanticEffect.CONTINUITY,
            WaitingPeriodSemanticEffect.PORTABILITY,
            WaitingPeriodSemanticEffect.SUM_INSURED_ENHANCEMENT,
        ),
        _rule(
            "wp_specific_disease_procedure",
            ("specified disease", "specific disease", "specified procedure", "code-excl02", "code- excl02"),
            NormativeUnitKind.EXCLUSION,
            WaitingPeriodSemanticEffect.DURATION,
            WaitingPeriodSemanticEffect.SCOPE,
            WaitingPeriodSemanticEffect.EXCEPTION,
            WaitingPeriodSemanticEffect.PORTABILITY,
            WaitingPeriodSemanticEffect.SUM_INSURED_ENHANCEMENT,
        ),
        _rule(
            "wp_initial",
            ("30-day waiting period", "30 day waiting period", "initial waiting period", "code-excl03", "code- excl03"),
            NormativeUnitKind.EXCLUSION,
            WaitingPeriodSemanticEffect.DURATION,
            WaitingPeriodSemanticEffect.START_BASIS,
            WaitingPeriodSemanticEffect.EXCEPTION,
            WaitingPeriodSemanticEffect.SUM_INSURED_ENHANCEMENT,
        ),
        _rule(
            "wp_continuity_portability",
            ("continuous coverage", "continuity benefit", "continuity benefits", "portability"),
            NormativeUnitKind.MODIFICATION,
            WaitingPeriodSemanticEffect.CONTINUITY,
            WaitingPeriodSemanticEffect.PORTABILITY,
        ),
        _rule(
            "wp_sum_insured_change",
            ("enhanced sum insured", "enhancement of sum insured", "sum insured increase", "enhanced limit"),
            NormativeUnitKind.MODIFICATION,
            WaitingPeriodSemanticEffect.SUM_INSURED_ENHANCEMENT,
            WaitingPeriodSemanticEffect.APPLICABILITY,
        ),
        _rule(
            "wp_reduction",
            ("reduction in specific disease waiting period", "reduction in speciﬁc disease waiting period", "reduction in pre-existing disease waiting period"),
            NormativeUnitKind.MODIFICATION,
            WaitingPeriodSemanticEffect.REDUCTION,
            WaitingPeriodSemanticEffect.OPTIONAL_COVER_INTERACTION,
            WaitingPeriodSemanticEffect.CROSS_CONCEPT_RELATIONSHIP,
        ),
        _rule(
            "wp_waiver",
            ("waiting period will be waived", "waiting periods will be waived", "shall not apply to the extent of", "waiting periods do not apply"),
            NormativeUnitKind.RELATIONSHIP,
            WaitingPeriodSemanticEffect.WAIVER,
            WaitingPeriodSemanticEffect.BENEFIT_SCOPED_OVERRIDE,
            WaitingPeriodSemanticEffect.CROSS_CONCEPT_RELATIONSHIP,
        ),
        _rule(
            "wp_optional_cover",
            ("optional cover", "optional covers"),
            NormativeUnitKind.APPLICABILITY,
            WaitingPeriodSemanticEffect.OPTIONAL_COVER_INTERACTION,
            WaitingPeriodSemanticEffect.APPLICABILITY,
        ),
        _rule(
            "wp_renewal_reinstatement",
            ("renewal", "grace period", "reinstatement", "added to this policy", "new member"),
            NormativeUnitKind.CONDITION,
            WaitingPeriodSemanticEffect.RENEWAL_OR_REINSTATEMENT_EFFECT,
            WaitingPeriodSemanticEffect.CONTINUITY,
            WaitingPeriodSemanticEffect.APPLICABILITY,
        ),
        _rule(
            "wp_schedule_or_table_delegation",
            ("policy schedule", "product benefit table", "product beneﬁt table"),
            NormativeUnitKind.APPLICABILITY,
            WaitingPeriodSemanticEffect.DURATION,
            WaitingPeriodSemanticEffect.APPLICABILITY,
            WaitingPeriodSemanticEffect.EFFECTIVE_DATE_OR_VERSION,
        ),
    )

    envelope = ConceptRelevanceEnvelope(
        concept="waiting_periods",
        policy_version="waiting_period_policy_v1",
        rules=rules,
        required_source_classes=("POLICY_WORDING",),
    )
    return WaitingPeriodConceptPolicy(
        concept="waiting_periods",
        policy_version="waiting_period_policy_v1",
        envelope=envelope,
        allowed_relationship_types=(
            RelationshipType.MODIFIES,
            RelationshipType.WAIVES,
            RelationshipType.OVERRIDES,
            RelationshipType.DEPENDS_ON,
            RelationshipType.APPLIES_WHEN,
            RelationshipType.INTERACTS_WITH,
            RelationshipType.LIMITED_BY,
        ),
        semantic_effects=tuple(WaitingPeriodSemanticEffect),
    )


__all__ = [
    "WaitingPeriodConceptPolicy",
    "WaitingPeriodSemanticEffect",
    "waiting_period_concept_policy",
]
