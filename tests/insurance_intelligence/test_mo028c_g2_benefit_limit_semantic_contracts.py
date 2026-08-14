from __future__ import annotations

import pytest

from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    BenefitIdentityReference,
    BenefitLimitContractError,
    BenefitLimitMechanic,
    CostSharingApplicability,
    CostSharingInteractionRule,
    CostSharingMechanicType,
    CostSharingOrdering,
    EventScope,
    LimitKind,
    MonetaryAmount,
    PercentageBasis,
    TimeScope,
)
from insurance_intelligence.generic_knowledge.contracts import EvidenceReference


def _evidence(evidence_id: str, locator: str) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id="star_arogya_sanjeevani_policy_wording",
        source_document_version="2026-08",
        source_hash_sha256="a" * 64,
        locator=locator,
        authority_class="POLICY_WORDING",
    )


def _identity(concept_id: str) -> BenefitIdentityReference:
    return BenefitIdentityReference(
        concept_id=concept_id,
        alias_registry_version="mo028c_benefit_alias_registry_v1",
        alias_registry_snapshot_id="gcar_test_snapshot",
    )


CORE = (_evidence("core", "benefit-table"),)
SCOPE = (_evidence("scope", "scope-clause"),)
BOUND = (_evidence("bound", "benefit-table-bound"),)
INTERACTION = (_evidence("interaction", "copay-clause"),)


def test_fixed_currency_ambulance_per_hospitalization_is_representable() -> None:
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:road_ambulance"),
        limit_kind=LimitKind.FIXED_CURRENCY,
        amount=MonetaryAmount(2000),
        event_scope=EventScope.PER_HOSPITALIZATION,
        core_evidence_references=CORE,
        scope_evidence_references=SCOPE,
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.amount == MonetaryAmount(2000)
    assert mechanic.is_si_linked is False
    assert mechanic.equivalence_ready is False


def test_policy_period_scope_is_distinct_from_policy_year() -> None:
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:modern_treatment_group"),
        limit_kind=LimitKind.PERCENTAGE,
        percentage=50,
        percentage_basis=PercentageBasis.SUM_INSURED,
        time_scope=TimeScope.PER_POLICY_PERIOD,
        core_evidence_references=CORE,
        scope_evidence_references=SCOPE,
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.time_scope is TimeScope.PER_POLICY_PERIOD
    assert mechanic.time_scope is not TimeScope.PER_POLICY_YEAR
    assert mechanic.equivalence_ready is False


def test_cataract_percentage_ceiling_preserves_per_eye_and_per_policy_year() -> None:
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:cataract"),
        limit_kind=LimitKind.PERCENTAGE,
        percentage=25,
        percentage_basis=PercentageBasis.SUM_INSURED,
        ceiling_amount=MonetaryAmount(40000),
        time_scope=TimeScope.PER_POLICY_YEAR,
        event_scope=EventScope.PER_EYE,
        core_evidence_references=CORE,
        scope_evidence_references=SCOPE,
        bound_evidence_references=BOUND,
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.percentage == 25.0
    assert mechanic.ceiling_amount == MonetaryAmount(40000)
    assert mechanic.time_scope is TimeScope.PER_POLICY_YEAR
    assert mechanic.event_scope is EventScope.PER_EYE
    assert mechanic.is_si_linked is True
    assert mechanic.equivalence_ready is False


def test_percentage_is_not_artificially_capped_at_one_hundred() -> None:
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:modern_treatment_group"),
        limit_kind=LimitKind.PERCENTAGE,
        percentage=125,
        percentage_basis=PercentageBasis.SUM_INSURED,
        core_evidence_references=CORE,
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.percentage == 125.0


def test_up_to_sum_insured_is_distinct_and_si_linked() -> None:
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:ayush"),
        limit_kind=LimitKind.UP_TO_SUM_INSURED,
        core_evidence_references=CORE,
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.limit_kind is LimitKind.UP_TO_SUM_INSURED
    assert mechanic.is_si_linked is True
    assert mechanic.amount is None
    assert mechanic.percentage is None
    assert mechanic.equivalence_ready is False


def test_no_limit_is_affirmative_semantic_shape_and_forbids_scope() -> None:
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:ayush"),
        limit_kind=LimitKind.NO_LIMIT,
        core_evidence_references=CORE,
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.is_si_linked is False
    assert mechanic.equivalence_ready is False
    with pytest.raises(BenefitLimitContractError, match="NO_LIMIT forbids scope fields"):
        BenefitLimitMechanic(
            benefit_identity=_identity("health:benefit:ayush"),
            limit_kind=LimitKind.NO_LIMIT,
            time_scope=TimeScope.PER_POLICY_YEAR,
            core_evidence_references=CORE,
            scope_evidence_references=SCOPE,
            ontology_version="benefit_limits_v1",
        )


def test_percentage_composition_requires_basis_and_bound_provenance() -> None:
    with pytest.raises(BenefitLimitContractError, match="PercentageBasis"):
        BenefitLimitMechanic(
            benefit_identity=_identity("health:benefit:cataract"),
            limit_kind=LimitKind.PERCENTAGE,
            percentage=25,
            core_evidence_references=CORE,
            ontology_version="benefit_limits_v1",
        )
    with pytest.raises(BenefitLimitContractError, match="bound_evidence_references"):
        BenefitLimitMechanic(
            benefit_identity=_identity("health:benefit:cataract"),
            limit_kind=LimitKind.PERCENTAGE,
            percentage=25,
            percentage_basis=PercentageBasis.SUM_INSURED,
            ceiling_amount=MonetaryAmount(40000),
            core_evidence_references=CORE,
            ontology_version="benefit_limits_v1",
        )


def test_floor_must_not_exceed_ceiling() -> None:
    with pytest.raises(BenefitLimitContractError, match="floor_amount"):
        BenefitLimitMechanic(
            benefit_identity=_identity("health:benefit:cataract"),
            limit_kind=LimitKind.PERCENTAGE,
            percentage=25,
            percentage_basis=PercentageBasis.SUM_INSURED,
            floor_amount=MonetaryAmount(50000),
            ceiling_amount=MonetaryAmount(40000),
            core_evidence_references=CORE,
            bound_evidence_references=BOUND,
            ontology_version="benefit_limits_v1",
        )


def test_unknown_scope_blocks_equivalence_without_blocking_representation() -> None:
    rule = CostSharingInteractionRule(
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.EXEMPT,
        ordering=CostSharingOrdering.UNKNOWN,
        evidence_references=INTERACTION,
    )
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:road_ambulance"),
        limit_kind=LimitKind.FIXED_CURRENCY,
        amount=MonetaryAmount(2000),
        event_scope=EventScope.UNSPECIFIED,
        core_evidence_references=CORE,
        scope_evidence_references=SCOPE,
        cost_sharing_interactions=(rule,),
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.equivalence_ready is False


def test_known_before_after_and_unknown_ordering_remain_structurally_distinct() -> None:
    before = CostSharingInteractionRule(
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.BEFORE_LIMIT,
        evidence_references=INTERACTION,
    )
    after = CostSharingInteractionRule(
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.AFTER_LIMIT,
        evidence_references=INTERACTION,
    )
    unknown = CostSharingInteractionRule(
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.UNKNOWN,
        evidence_references=INTERACTION,
    )
    assert before != after
    assert before.equivalence_ready is True
    assert after.equivalence_ready is True
    assert unknown.equivalence_ready is False


def test_empty_interaction_inventory_blocks_equivalence() -> None:
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:road_ambulance"),
        limit_kind=LimitKind.FIXED_CURRENCY,
        amount=MonetaryAmount(2000),
        core_evidence_references=CORE,
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.cost_sharing_interactions == ()
    assert mechanic.equivalence_ready is False


def test_known_exemption_can_make_interaction_dimension_equivalence_ready() -> None:
    rule = CostSharingInteractionRule(
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.EXEMPT,
        ordering=CostSharingOrdering.UNKNOWN,
        evidence_references=INTERACTION,
    )
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:road_ambulance"),
        limit_kind=LimitKind.FIXED_CURRENCY,
        amount=MonetaryAmount(2000),
        core_evidence_references=CORE,
        cost_sharing_interactions=(rule,),
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.equivalence_ready is True


def test_unknown_interaction_applicability_blocks_equivalence() -> None:
    rule = CostSharingInteractionRule(
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.UNKNOWN,
        ordering=CostSharingOrdering.UNKNOWN,
        evidence_references=INTERACTION,
    )
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:cataract"),
        limit_kind=LimitKind.PERCENTAGE,
        percentage=25,
        percentage_basis=PercentageBasis.SUM_INSURED,
        ceiling_amount=MonetaryAmount(40000),
        time_scope=TimeScope.PER_POLICY_YEAR,
        event_scope=EventScope.PER_EYE,
        core_evidence_references=CORE,
        scope_evidence_references=SCOPE,
        bound_evidence_references=BOUND,
        cost_sharing_interactions=(rule,),
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.equivalence_ready is False


def test_exempt_or_unknown_applicability_cannot_claim_ordering() -> None:
    for applies in (
        CostSharingApplicability.EXEMPT,
        CostSharingApplicability.UNKNOWN,
    ):
        with pytest.raises(BenefitLimitContractError, match="requires UNKNOWN ordering"):
            CostSharingInteractionRule(
                mechanic_type=CostSharingMechanicType.COPAY,
                applies=applies,
                ordering=CostSharingOrdering.AFTER_LIMIT,
                evidence_references=INTERACTION,
            )


def test_proportionate_deduction_is_representable_without_claim_arithmetic() -> None:
    rule = CostSharingInteractionRule(
        mechanic_type=CostSharingMechanicType.PROPORTIONATE_DEDUCTION,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.UNKNOWN,
        evidence_references=(_evidence("prop", "room-rent-proportionate-deduction"),),
    )
    mechanic = BenefitLimitMechanic(
        benefit_identity=_identity("health:benefit:room_rent"),
        limit_kind=LimitKind.PERCENTAGE,
        percentage=1,
        percentage_basis=PercentageBasis.SUM_INSURED,
        ceiling_amount=MonetaryAmount(5000),
        time_scope=TimeScope.PER_DAY,
        core_evidence_references=CORE,
        scope_evidence_references=SCOPE,
        bound_evidence_references=BOUND,
        cost_sharing_interactions=(rule,),
        ontology_version="benefit_limits_v1",
    )
    assert mechanic.cost_sharing_interactions == (rule,)
    assert mechanic.equivalence_ready is False


def test_fixed_currency_rejects_percentage_fields_and_g2_is_inr_only() -> None:
    with pytest.raises(BenefitLimitContractError, match="FIXED_CURRENCY forbids"):
        BenefitLimitMechanic(
            benefit_identity=_identity("health:benefit:road_ambulance"),
            limit_kind=LimitKind.FIXED_CURRENCY,
            amount=MonetaryAmount(2000),
            percentage=10,
            core_evidence_references=CORE,
            ontology_version="benefit_limits_v1",
        )
    with pytest.raises(BenefitLimitContractError, match="INR only"):
        MonetaryAmount(100, "USD")


def test_health_benefit_identity_namespace_is_required() -> None:
    with pytest.raises(BenefitLimitContractError, match="health benefit concept"):
        BenefitIdentityReference(
            concept_id="health:concept:sub_limit",
            alias_registry_version="v1",
            alias_registry_snapshot_id="snapshot",
        )
