from __future__ import annotations

import pytest

from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    CostSharingApplicability,
    CostSharingMechanicType,
    CostSharingOrdering,
    EventScope,
    LimitKind,
    MonetaryAmount,
    PercentageBasis,
    TimeScope,
)
from insurance_intelligence.generic_knowledge.benefit_limit_reviewed_propositions import (
    DimensionEvidenceBinding,
    InteractionTargetMode,
    PropositionDimension,
    ReviewedBenefitLimitProposition,
    ReviewedBenefitLimitPropositionError,
    ReviewedCostSharingInteraction,
)
from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey, EvidenceReference


def _evidence(evidence_id: str, locator: str = "benefit-table") -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id="star_arogya_sanjeevani_policy_wording",
        source_document_version="2026-08",
        source_hash_sha256="a" * 64,
        locator=locator,
        authority_class="POLICY_WORDING",
    )


def _base(policy_version: str = "v1") -> ApplicabilityKey:
    return ApplicabilityKey(
        product_reference="star_health:arogya_sanjeevani",
        policy_version=policy_version,
    )


def _binding(dimension: PropositionDimension, *ids: str) -> DimensionEvidenceBinding:
    return DimensionEvidenceBinding(
        dimension=dimension,
        evidence_ids=tuple(ids),
        review_decision_id=f"review:{dimension.value}",
    )


def test_source_supported_cataract_proposition_is_valid() -> None:
    evidence = (_evidence("core"), _evidence("scope", "scope-clause"), _evidence("bound"))
    proposition = ReviewedBenefitLimitProposition(
        normative_unit_id="cataract-limit",
        raw_benefit_label="Cataract",
        limit_kind=LimitKind.PERCENTAGE,
        percentage=25,
        percentage_basis=PercentageBasis.SUM_INSURED,
        ceiling_amount=MonetaryAmount(40000),
        time_scope=TimeScope.PER_POLICY_YEAR,
        event_scope=EventScope.PER_EYE,
        base_applicability=_base(),
        evidence_references=evidence,
        dimension_evidence_bindings=(
            _binding(PropositionDimension.BENEFIT_LABEL, "core"),
            _binding(PropositionDimension.VALUE_KIND, "core"),
            _binding(PropositionDimension.PERCENTAGE, "core"),
            _binding(PropositionDimension.PERCENTAGE_BASIS, "core"),
            _binding(PropositionDimension.CEILING, "bound"),
            _binding(PropositionDimension.TIME_SCOPE, "scope"),
            _binding(PropositionDimension.EVENT_SCOPE, "scope"),
        ),
        review_decision_id="review:cataract",
    )
    assert proposition.event_scope is EventScope.PER_EYE


def test_asserted_event_scope_without_evidence_binding_fails_closed() -> None:
    with pytest.raises(ReviewedBenefitLimitPropositionError, match="EVENT_SCOPE"):
        ReviewedBenefitLimitProposition(
            normative_unit_id="cataract-limit",
            raw_benefit_label="Cataract",
            limit_kind=LimitKind.PERCENTAGE,
            percentage=25,
            percentage_basis=PercentageBasis.SUM_INSURED,
            event_scope=EventScope.PER_EYE,
            base_applicability=_base(),
            evidence_references=(_evidence("core"),),
            dimension_evidence_bindings=(
                _binding(PropositionDimension.BENEFIT_LABEL, "core"),
                _binding(PropositionDimension.VALUE_KIND, "core"),
                _binding(PropositionDimension.PERCENTAGE, "core"),
                _binding(PropositionDimension.PERCENTAGE_BASIS, "core"),
            ),
            review_decision_id="review:cataract",
        )


def test_asserted_ceiling_without_bound_binding_fails_closed() -> None:
    with pytest.raises(ReviewedBenefitLimitPropositionError, match="CEILING"):
        ReviewedBenefitLimitProposition(
            normative_unit_id="cataract-limit",
            raw_benefit_label="Cataract",
            limit_kind=LimitKind.PERCENTAGE,
            percentage=25,
            percentage_basis=PercentageBasis.SUM_INSURED,
            ceiling_amount=MonetaryAmount(40000),
            base_applicability=_base(),
            evidence_references=(_evidence("core"),),
            dimension_evidence_bindings=(
                _binding(PropositionDimension.BENEFIT_LABEL, "core"),
                _binding(PropositionDimension.VALUE_KIND, "core"),
                _binding(PropositionDimension.PERCENTAGE, "core"),
                _binding(PropositionDimension.PERCENTAGE_BASIS, "core"),
            ),
            review_decision_id="review:cataract",
        )


def test_binding_to_unknown_evidence_id_fails_closed() -> None:
    with pytest.raises(ReviewedBenefitLimitPropositionError, match="unknown evidence_id"):
        ReviewedBenefitLimitProposition(
            normative_unit_id="ambulance-limit",
            raw_benefit_label="Road Ambulance",
            limit_kind=LimitKind.FIXED_CURRENCY,
            amount=MonetaryAmount(2000),
            base_applicability=_base(),
            evidence_references=(_evidence("core"),),
            dimension_evidence_bindings=(
                _binding(PropositionDimension.BENEFIT_LABEL, "core"),
                _binding(PropositionDimension.VALUE_KIND, "core"),
                _binding(PropositionDimension.AMOUNT, "missing"),
            ),
            review_decision_id="review:ambulance",
        )


def test_internal_shape_defect_is_rejected_before_mapping() -> None:
    with pytest.raises(ReviewedBenefitLimitPropositionError, match="NO_LIMIT"):
        ReviewedBenefitLimitProposition(
            normative_unit_id="bad-no-limit",
            raw_benefit_label="AYUSH",
            limit_kind=LimitKind.NO_LIMIT,
            amount=MonetaryAmount(50000),
            base_applicability=_base(),
            evidence_references=(_evidence("core"),),
            dimension_evidence_bindings=(
                _binding(PropositionDimension.BENEFIT_LABEL, "core"),
                _binding(PropositionDimension.VALUE_KIND, "core"),
                _binding(PropositionDimension.AMOUNT, "core"),
            ),
            review_decision_id="review:bad",
        )


def test_typed_si_band_cannot_coexist_with_legacy_string_band() -> None:
    with pytest.raises(ReviewedBenefitLimitPropositionError, match="sum_insured_band"):
        ReviewedBenefitLimitProposition(
            normative_unit_id="banded",
            raw_benefit_label="Cataract",
            limit_kind=LimitKind.FIXED_CURRENCY,
            amount=MonetaryAmount(40000),
            base_applicability=ApplicabilityKey(
                product_reference="star_health:arogya_sanjeevani",
                policy_version="v1",
                sum_insured_band="5L-10L",
            ),
            sum_insured_band_payload={"lower": 500000, "upper": 1000000},
            evidence_references=(_evidence("core"),),
            dimension_evidence_bindings=(
                _binding(PropositionDimension.BENEFIT_LABEL, "core"),
                _binding(PropositionDimension.VALUE_KIND, "core"),
                _binding(PropositionDimension.AMOUNT, "core"),
                _binding(PropositionDimension.SI_BAND, "core"),
            ),
            review_decision_id="review:band",
        )


def test_explicit_interaction_targets_require_source_supported_target_scope() -> None:
    interaction = ReviewedCostSharingInteraction(
        normative_unit_id="global-copay",
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.UNKNOWN,
        target_mode=InteractionTargetMode.EXPLICIT_CONCEPT_SET,
        target_benefit_concept_ids=(
            "health:benefit:cataract",
            "health:benefit:road_ambulance",
        ),
        base_applicability=_base(),
        evidence_references=(_evidence("copay", "copay-clause"),),
        dimension_evidence_bindings=(
            _binding(PropositionDimension.INTERACTION_APPLICABILITY, "copay"),
            _binding(PropositionDimension.INTERACTION_ORDERING, "copay"),
            _binding(PropositionDimension.INTERACTION_TARGET_SCOPE, "copay"),
        ),
        review_decision_id="review:global-copay",
    )
    assert interaction.target_benefit_concept_ids == (
        "health:benefit:cataract",
        "health:benefit:road_ambulance",
    )


def test_interaction_target_scope_without_evidence_binding_fails_closed() -> None:
    with pytest.raises(ReviewedBenefitLimitPropositionError, match="INTERACTION_TARGET_SCOPE"):
        ReviewedCostSharingInteraction(
            normative_unit_id="global-copay",
            mechanic_type=CostSharingMechanicType.COPAY,
            applies=CostSharingApplicability.YES,
            ordering=CostSharingOrdering.UNKNOWN,
            target_mode=InteractionTargetMode.EXPLICIT_CONCEPT_SET,
            target_benefit_concept_ids=("health:benefit:cataract",),
            base_applicability=_base(),
            evidence_references=(_evidence("copay", "copay-clause"),),
            dimension_evidence_bindings=(
                _binding(PropositionDimension.INTERACTION_APPLICABILITY, "copay"),
                _binding(PropositionDimension.INTERACTION_ORDERING, "copay"),
            ),
            review_decision_id="review:global-copay",
        )


def test_product_wide_scope_uses_governed_scope_identity_not_inferred_target_list() -> None:
    interaction = ReviewedCostSharingInteraction(
        normative_unit_id="global-copay",
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.UNKNOWN,
        target_mode=InteractionTargetMode.PRODUCT_WIDE_GOVERNED_SCOPE,
        governed_product_scope_id="scope:arogya:all-governed-benefits:v1",
        base_applicability=_base(),
        evidence_references=(_evidence("copay", "copay-clause"),),
        dimension_evidence_bindings=(
            _binding(PropositionDimension.INTERACTION_APPLICABILITY, "copay"),
            _binding(PropositionDimension.INTERACTION_ORDERING, "copay"),
            _binding(PropositionDimension.INTERACTION_TARGET_SCOPE, "copay"),
        ),
        review_decision_id="review:global-copay",
    )
    assert interaction.target_benefit_concept_ids == ()
    assert interaction.governed_product_scope_id.startswith("scope:")


def test_product_wide_scope_rejects_manual_target_list() -> None:
    with pytest.raises(ReviewedBenefitLimitPropositionError, match="forbids explicit"):
        ReviewedCostSharingInteraction(
            normative_unit_id="global-copay",
            mechanic_type=CostSharingMechanicType.COPAY,
            applies=CostSharingApplicability.YES,
            ordering=CostSharingOrdering.UNKNOWN,
            target_mode=InteractionTargetMode.PRODUCT_WIDE_GOVERNED_SCOPE,
            target_benefit_concept_ids=("health:benefit:cataract",),
            governed_product_scope_id="scope:v1",
            base_applicability=_base(),
            evidence_references=(_evidence("copay"),),
            dimension_evidence_bindings=(
                _binding(PropositionDimension.INTERACTION_APPLICABILITY, "copay"),
                _binding(PropositionDimension.INTERACTION_ORDERING, "copay"),
                _binding(PropositionDimension.INTERACTION_TARGET_SCOPE, "copay"),
            ),
            review_decision_id="review:global-copay",
        )
