from __future__ import annotations

from dataclasses import replace

from insurance_intelligence.evaluation.certification_decision import (
    CertificationConfidenceMode,
    CertificationDecisionPolicy,
    ControlledCertificationStatus,
    HumanCertificationReview,
    HumanReviewDecision,
    decide_controlled_certification,
)
from insurance_intelligence.evaluation.cross_provider_repeat_run import (
    CrossProviderRepeatRunEvidence,
)


def _evidence(
    *,
    confidence: float = 0.99,
    status: str = "CROSS_PROVIDER_SEMANTICALLY_STABLE",
    exact_agreement: bool = True,
    all_matched: bool = True,
    hard_failure_free: bool = True,
    unresolved_free: bool = True,
):
    return CrossProviderRepeatRunEvidence(
        batch_id="batch-1",
        schema_version="1.0",
        contract_id="contract-1",
        rule_family_id="CONDITIONAL_COPAYMENT",
        rule_family_version="1.0",
        renderer_model="renderer-model",
        renderer_prompt_version="renderer-v1",
        openai_extractor_model="openai-model",
        openai_extractor_prompt_version="openai-v1",
        gemini_extractor_model="gemini-model",
        gemini_extractor_prompt_version="gemini-v1",
        data_classification="PUBLIC",
        required_run_count=3,
        completed_run_count=3,
        exact_agreement_every_run=exact_agreement,
        all_components_matched=all_matched,
        hard_failure_free=hard_failure_free,
        unresolved_free=unresolved_free,
        preflight_passed_every_run=True,
        minimum_observed_confidence=confidence,
        observations=(),
        certification_effect="NONE",
        certification_granted=False,
        status=status,
    )


def _policy_v1():
    return CertificationDecisionPolicy(
        policy_id="controlled-certification-v1",
        minimum_confidence=0.95,
    )


def _policy_v2():
    return CertificationDecisionPolicy(
        policy_id="controlled-certification-v2",
        minimum_confidence=0.95,
        confidence_mode=CertificationConfidenceMode.DETERMINISTIC_PROOF_PRIMARY,
    )


def _approval():
    return HumanCertificationReview(
        reviewer_id="reviewer-1",
        decision=HumanReviewDecision.APPROVE,
        reviewed_evidence_ids=("evidence-1",),
        rationale="Evidence and governed tuple reviewed.",
    )


def test_v1_stable_high_confidence_evidence_requires_human_approval():
    decision = decide_controlled_certification(
        _evidence(),
        policy=_policy_v1(),
        approved_evidence_ids=("evidence-1",),
        human_review=None,
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert decision.reason_codes == ("HUMAN_APPROVAL_REQUIRED",)
    assert decision.certification_granted is False
    assert decision.certification_effect == "NONE"


def test_v1_stable_high_confidence_evidence_can_be_certified_after_approval():
    decision = decide_controlled_certification(
        _evidence(),
        policy=_policy_v1(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.CERTIFIED
    assert decision.reason_codes == ()
    assert decision.certification_granted is True
    assert decision.certification_effect == "GRANT"


def test_v1_point_nine_confidence_remains_review_only_after_approval():
    decision = decide_controlled_certification(
        _evidence(confidence=0.9),
        policy=_policy_v1(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert decision.reason_codes == ("MINIMUM_CONFIDENCE_NOT_MET",)


def test_v2_exact_deterministic_proof_can_certify_at_point_nine_confidence():
    decision = decide_controlled_certification(
        _evidence(confidence=0.9),
        policy=_policy_v2(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.CERTIFIED
    assert decision.reason_codes == ()
    assert decision.confidence_mode is CertificationConfidenceMode.DETERMINISTIC_PROOF_PRIMARY
    assert decision.minimum_observed_confidence == 0.9
    assert decision.minimum_required_confidence == 0.95


def test_v2_still_requires_human_approval():
    decision = decide_controlled_certification(
        _evidence(confidence=0.9),
        policy=_policy_v2(),
        approved_evidence_ids=("evidence-1",),
        human_review=None,
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert decision.reason_codes == ("HUMAN_APPROVAL_REQUIRED",)


def test_v2_high_confidence_cannot_compensate_for_unresolved_semantics():
    decision = decide_controlled_certification(
        _evidence(confidence=1.0, unresolved_free=False),
        policy=_policy_v2(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert "UNRESOLVED_COMPONENT_PRESENT" in decision.reason_codes


def test_v2_high_confidence_cannot_compensate_for_provider_disagreement():
    decision = decide_controlled_certification(
        _evidence(confidence=1.0, exact_agreement=False),
        policy=_policy_v2(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert "EXACT_AGREEMENT_NOT_PROVEN" in decision.reason_codes


def test_v2_hard_failure_prevents_certification():
    decision = decide_controlled_certification(
        _evidence(confidence=1.0, hard_failure_free=False),
        policy=_policy_v2(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert "HARD_FAILURE_PRESENT" in decision.reason_codes


def test_human_rejection_is_authoritative_in_both_modes():
    rejected = replace(_approval(), decision=HumanReviewDecision.REJECT)
    for policy in (_policy_v1(), _policy_v2()):
        decision = decide_controlled_certification(
            _evidence(),
            policy=policy,
            approved_evidence_ids=("evidence-1",),
            human_review=rejected,
        )
        assert decision.status is ControlledCertificationStatus.REJECTED
        assert "HUMAN_REVIEW_REJECTED" in decision.reason_codes
        assert decision.certification_granted is False
