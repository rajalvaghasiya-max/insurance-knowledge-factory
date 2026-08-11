from datetime import date

import pytest

from insurance_intelligence.generic_knowledge.authority_resolution import (
    AuthorityClass,
    AuthorityResolution,
    ResolutionStatus as AuthorityResolutionStatus,
)
from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    PublicationBlocker,
    PublicationBlockerCode,
)
from insurance_intelligence.generic_knowledge.governance_integration import (
    AnswerShape,
    AuthorityResolutionOutcome,
    GovernanceIntegrationError,
    GovernanceLayer,
    InstanceResolutionAssessment,
    RegulatoryEffectClass,
    RegulatoryInterpretationState,
    SemanticPublicationState,
    assess_endorsement_release,
    assess_regulatory_interpretation,
    assess_semantic_publication,
    authority_outcome,
    document_authority_capability,
)
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    PublicationDependencyBinding,
    PublicationEligibilityDecision,
    PublicationEligibilityStatus,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    ResolutionInputs,
    ResolutionStatus,
    ValueSource,
    compute_resolution_status,
)
from insurance_intelligence.generic_knowledge.waiting_period_schedule_resolution import (
    InstanceDocumentClass,
)


def _app():
    return ApplicabilityKey(product_reference="generic:product")


def _binding():
    return PublicationDependencyBinding(
        ontology_version="ont-v1",
        source_document_id="wording-1",
        source_document_version="v1",
        source_hash_sha256="abc123",
        review_decision_version="review-v1",
    )


def _decision(*, blockers=()):
    return PublicationEligibilityDecision(
        status=(PublicationEligibilityStatus.BLOCKED if blockers else PublicationEligibilityStatus.ELIGIBLE),
        concept="waiting_period",
        applicability=_app(),
        dependency_binding=_binding(),
        blockers=tuple(blockers),
    )


def _authority(status, *, selected_class=None):
    return AuthorityResolution(
        status=status,
        concept="waiting_period",
        semantic_key="ped",
        as_of_date=date(2026, 8, 11),
        selected_candidate_ids=("selected",) if status is AuthorityResolutionStatus.RESOLVED else (),
        selected_authority_class=selected_class,
        semantic_value={"months": 36} if status is AuthorityResolutionStatus.RESOLVED else None,
        rejected_candidate_ids=(),
        conflict_candidate_ids=("a", "b") if status is AuthorityResolutionStatus.CONFLICTED else (),
        regulatory_overlay_applied=(selected_class is AuthorityClass.REGULATORY_OVERLAY),
    )


def test_schedule_is_value_authority_only():
    capability = document_authority_capability(InstanceDocumentClass.SCHEDULE)
    assert capability.may_supply_instance_values is True
    assert capability.may_supply_semantics is False
    assert capability.requires_semantic_review is False


def test_endorsement_carries_semantics_and_values_under_review_gate():
    capability = document_authority_capability(InstanceDocumentClass.ENDORSEMENT)
    assert capability.may_supply_semantics is True
    assert capability.may_supply_instance_values is True
    assert capability.requires_semantic_review is True


def test_rider_carries_semantics_and_values_under_review_gate():
    capability = document_authority_capability(InstanceDocumentClass.RIDER)
    assert capability.may_supply_semantics is True
    assert capability.may_supply_instance_values is True
    assert capability.requires_semantic_review is True


def test_certificate_has_no_authority_by_default():
    capability = document_authority_capability(InstanceDocumentClass.CERTIFICATE)
    assert capability.may_supply_semantics is False
    assert capability.may_supply_instance_values is False


def test_endorsement_value_and_semantics_stay_quarantined_before_review():
    assessment = assess_endorsement_release(
        InstanceDocumentClass.ENDORSEMENT,
        semantic_review_approved=False,
    )
    assert assessment.semantics_released is False
    assert assessment.values_released is False


def test_endorsement_semantics_and_value_release_together_after_review():
    assessment = assess_endorsement_release(
        InstanceDocumentClass.ENDORSEMENT,
        semantic_review_approved=True,
    )
    assert assessment.semantics_released is True
    assert assessment.values_released is True


def test_non_endorsement_cannot_use_endorsement_release_gate():
    with pytest.raises(GovernanceIntegrationError):
        assess_endorsement_release(InstanceDocumentClass.SCHEDULE, semantic_review_approved=True)


def test_reduce_only_unverified_overlay_allows_conservative_contract_publication():
    assessment = assess_regulatory_interpretation(
        verification_required=True,
        effect_class=RegulatoryEffectClass.REDUCE_ONLY,
    )
    assert assessment.state is RegulatoryInterpretationState.VERIFICATION_REQUIRED
    assert assessment.contract_fact_publishable is True
    assert assessment.answer_shape is AnswerShape.CONDITIONAL


def test_benefit_establishing_overlay_cannot_publish_affirmative_benefit():
    assessment = assess_regulatory_interpretation(
        verification_required=True,
        effect_class=RegulatoryEffectClass.BENEFIT_ESTABLISHING,
    )
    assert assessment.state is RegulatoryInterpretationState.VERIFICATION_REQUIRED
    assert assessment.contract_fact_publishable is False
    assert assessment.answer_shape is AnswerShape.UNQUANTIFIED


def test_mixed_or_unknown_overlay_fails_closed():
    assessment = assess_regulatory_interpretation(
        verification_required=True,
        effect_class=RegulatoryEffectClass.MIXED_OR_UNKNOWN,
    )
    assert assessment.state is RegulatoryInterpretationState.BLOCKED
    assert assessment.contract_fact_publishable is False
    assert assessment.answer_shape is AnswerShape.UNQUANTIFIED


def test_verified_overlay_can_be_scalar():
    assessment = assess_regulatory_interpretation(
        verification_required=False,
        effect_class=RegulatoryEffectClass.BENEFIT_ESTABLISHING,
    )
    assert assessment.state is RegulatoryInterpretationState.RESOLVED
    assert assessment.answer_shape is AnswerShape.SCALAR


def test_well_formed_instance_bound_domain_does_not_block_semantic_publication():
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.SCALAR,
        well_formed_instance_domain=True,
    )
    assert assessment.state is SemanticPublicationState.ELIGIBLE
    assert assessment.blockers == ()


def test_degenerate_instance_domain_is_representation_blocker():
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.UNQUANTIFIED,
        well_formed_instance_domain=False,
    )
    assert assessment.state is SemanticPublicationState.BLOCKED
    assert "NOT_YET_REPRESENTABLE" in assessment.blockers


def test_conditional_fact_can_publish_but_is_not_scalar():
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.CONDITIONAL,
    )
    assert assessment.state is SemanticPublicationState.ELIGIBLE
    assert assessment.answer_shape is AnswerShape.CONDITIONAL


def test_range_fact_can_publish_but_is_not_scalar():
    assessment = assess_semantic_publication(_decision(), answer_shape=AnswerShape.RANGE)
    assert assessment.state is SemanticPublicationState.ELIGIBLE
    assert assessment.answer_shape is AnswerShape.RANGE


def test_machine_detected_semantic_conflict_routes_to_review_not_terminal_block():
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.UNQUANTIFIED,
        machine_semantic_conflict_detected=True,
    )
    assert assessment.state is SemanticPublicationState.REVIEW_REQUIRED
    assert assessment.review_requirement_ids == ("candidate_semantic_conflict",)


def test_source_stale_is_semantic_stale_not_generic_instance_failure():
    blocker = PublicationBlocker(
        blocker_id="source-stale",
        code=PublicationBlockerCode.SOURCE_STALE,
        concept="waiting_period",
        applicability=_app(),
        reason="semantic source stale",
    )
    assessment = assess_semantic_publication(
        _decision(blockers=(blocker,)),
        answer_shape=AnswerShape.UNQUANTIFIED,
    )
    assert assessment.state is SemanticPublicationState.STALE


def test_legacy_recertification_blocks_only_assessed_unit():
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.SCALAR,
        legacy_recertification_required=True,
    )
    assert assessment.state is SemanticPublicationState.BLOCKED
    assert "LEGACY_RECERTIFICATION_REQUIRED" in assessment.blockers
    unrelated = assess_semantic_publication(_decision(), answer_shape=AnswerShape.SCALAR)
    assert unrelated.state is SemanticPublicationState.ELIGIBLE


def test_governance_blocked_operand_blocks_relationship_publication():
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.CONDITIONAL,
        required_operand_governance_blocked=True,
    )
    assert assessment.state is SemanticPublicationState.BLOCKED
    assert "OPERAND_GOVERNANCE_BLOCKED" in assessment.blockers


def test_benefit_establishing_regulatory_assessment_blocks_semantic_affirmation():
    regulatory = assess_regulatory_interpretation(
        verification_required=True,
        effect_class=RegulatoryEffectClass.BENEFIT_ESTABLISHING,
    )
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.UNQUANTIFIED,
        regulatory_assessment=regulatory,
    )
    assert assessment.state is SemanticPublicationState.BLOCKED
    assert "UNSAFE_UNVERIFIED_REGULATORY_EFFECT" in assessment.blockers


def test_reduce_only_regulatory_assessment_does_not_block_base_publication():
    regulatory = assess_regulatory_interpretation(
        verification_required=True,
        effect_class=RegulatoryEffectClass.REDUCE_ONLY,
    )
    assessment = assess_semantic_publication(
        _decision(),
        answer_shape=AnswerShape.CONDITIONAL,
        regulatory_assessment=regulatory,
    )
    assert assessment.state is SemanticPublicationState.ELIGIBLE
    assert assessment.warnings


def test_existing_authority_conflict_adapts_to_unresolved_authority_conflict():
    outcome = authority_outcome(_authority(AuthorityResolutionStatus.CONFLICTED, selected_class=AuthorityClass.POLICY_WORDING))
    assert outcome is AuthorityResolutionOutcome.UNRESOLVED_AUTHORITY_CONFLICT


def test_existing_authority_resolution_can_express_authoritative_override():
    outcome = authority_outcome(
        _authority(AuthorityResolutionStatus.RESOLVED, selected_class=AuthorityClass.POLICY_WORDING),
        lower_authority_candidate_present=True,
    )
    assert outcome is AuthorityResolutionOutcome.AUTHORITATIVE_OVERRIDE


def test_existing_authority_resolution_without_lower_candidate_is_no_conflict():
    outcome = authority_outcome(
        _authority(AuthorityResolutionStatus.RESOLVED, selected_class=AuthorityClass.POLICY_WORDING)
    )
    assert outcome is AuthorityResolutionOutcome.NO_CONFLICT


def test_instance_assessment_requires_instance_layer_and_keeps_resolution_separate():
    resolution = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    assessment = InstanceResolutionAssessment(
        layer=GovernanceLayer.INSTANCE_VALUE,
        resolution=resolution,
        policy_instance_reference="policy-123",
        resolution_cell_identity=("ped", "base"),
    )
    assert assessment.resolution.status is ResolutionStatus.POLICY_SCHEDULE_BOUND


def test_instance_status_is_not_input_to_semantic_publication_assessment():
    # Contract-level guard: semantic publication consumes G7 decision plus semantic governance
    # inputs; it does not accept a C1 resolution-status argument that could be blindly translated.
    with pytest.raises(TypeError):
        assess_semantic_publication(
            _decision(),
            answer_shape=AnswerShape.SCALAR,
            instance_resolution_status=ResolutionStatus.POLICY_SCHEDULE_BOUND,
        )
