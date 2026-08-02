from __future__ import annotations

from dataclasses import replace

from insurance_intelligence.evaluation.certification_decision import (
    CertificationDecisionPolicy,
    ControlledCertificationStatus,
    HumanCertificationReview,
    HumanReviewDecision,
    decide_controlled_certification,
)
from insurance_intelligence.evaluation.cross_provider_repeat_run import (
    CrossProviderRepeatRunEvidence,
)


def _evidence(*, confidence: float = 0.99, status: str = "CROSS_PROVIDER_SEMANTICALLY_STABLE"):
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
        exact_agreement_every_run=True,
        all_components_matched=True,
        hard_failure_free=True,
        unresolved_free=True,
        preflight_passed_every_run=True,
        minimum_observed_confidence=confidence,
        observations=(),
        certification_effect="NONE",
        certification_granted=False,
        status=status,
    )


def _policy():
    return CertificationDecisionPolicy(
        policy_id="controlled-certification-v1",
        minimum_confidence=0.95,
    )


def _approval():
    return HumanCertificationReview(
        reviewer_id="reviewer-1",
        decision=HumanReviewDecision.APPROVE,
        reviewed_evidence_ids=("evidence-1",),
        rationale="Evidence and governed tuple reviewed.",
    )


def test_stable_high_confidence_evidence_requires_human_approval():
    decision = decide_controlled_certification(
        _evidence(),
        policy=_policy(),
        approved_evidence_ids=("evidence-1",),
        human_review=None,
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert decision.reason_codes == ("HUMAN_APPROVAL_REQUIRED",)
    assert decision.certification_granted is False
    assert decision.certification_effect == "NONE"


def test_stable_high_confidence_evidence_can_be_certified_after_approval():
    decision = decide_controlled_certification(
        _evidence(),
        policy=_policy(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.CERTIFIED
    assert decision.reason_codes == ()
    assert decision.certification_granted is True
    assert decision.certification_effect == "GRANT"


def test_current_point_nine_confidence_remains_review_only_even_after_approval():
    decision = decide_controlled_certification(
        _evidence(confidence=0.9),
        policy=_policy(),
        approved_evidence_ids=("evidence-1",),
        human_review=_approval(),
    )

    assert decision.status is ControlledCertificationStatus.REVIEW_ONLY
    assert decision.reason_codes == ("MINIMUM_CONFIDENCE_NOT_MET",)
    assert decision.certification_granted is False


def test_human_rejection_is_authoritative():
    rejected = replace(_approval(), decision=HumanReviewDecision.REJECT)
    decision = decide_controlled_certification(
        _evidence(),
        policy=_policy(),
        approved_evidence_ids=("evidence-1",),
        human_review=rejected,
    )

    assert decision.status is ControlledCertificationStatus.REJECTED
    assert decision.reason_codes == ("HUMAN_REVIEW_REJECTED",)
    assert decision.certification_granted is False
