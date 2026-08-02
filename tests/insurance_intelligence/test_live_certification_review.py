import pytest

from insurance_intelligence.evaluation.live_certification_review import (
    LiveCertificationReviewError,
    LiveCertificationReviewerDecision,
    build_governed_live_review,
)


def _evidence():
    return {
        "evidence_id": "live-certification-evidence-test",
        "source_artifact_sha256": "a" * 64,
        "contract_id": "contract-star-comprehensive-conditional-copay-v1",
        "certification_effect": "NONE",
        "certification_granted": False,
        "reviewer_decision": "PENDING",
        "routing_reason_codes": [
            "LOW_EXTRACTION_CONFIDENCE",
            "RULE_FAMILY_NOT_CERTIFIED",
        ],
        "hard_failure_codes": [],
        "unresolved_component_ids": [],
        "components": [
            {"component_id": "entry-age-trigger", "status": "MATCHED"},
            {"component_id": "copay-effect", "status": "MATCHED"},
            {"component_id": "continuous-renewal-exception", "status": "MATCHED"},
            {"component_id": "applicability-scope", "status": "MATCHED"},
        ],
    }


def test_approval_creates_non_certifying_review_record():
    record = build_governed_live_review(
        _evidence(),
        reviewer_id="reviewer-rajal",
        reviewed_at="2026-08-02T10:30:00+05:30",
        decision=LiveCertificationReviewerDecision.APPROVED_FOR_CERTIFICATION_CONSIDERATION,
        rationale="All canonical components match; low confidence is acknowledged for manual review.",
    )

    assert record.decision is LiveCertificationReviewerDecision.APPROVED_FOR_CERTIFICATION_CONSIDERATION
    assert record.certification_effect == "NONE"
    assert record.certification_granted is False
    assert record.reviewed_component_ids == tuple(sorted(record.reviewed_component_ids))
    assert record.acknowledged_reason_codes == (
        "LOW_EXTRACTION_CONFIDENCE",
        "RULE_FAMILY_NOT_CERTIFIED",
    )


def test_approval_is_forbidden_when_hard_failure_exists():
    evidence = _evidence()
    evidence["hard_failure_codes"] = ["SEMANTIC_VALUE_CHANGED"]

    with pytest.raises(LiveCertificationReviewError, match="hard failures"):
        build_governed_live_review(
            evidence,
            reviewer_id="reviewer-rajal",
            reviewed_at="2026-08-02T10:30:00+05:30",
            decision=LiveCertificationReviewerDecision.APPROVED_FOR_CERTIFICATION_CONSIDERATION,
            rationale="Approve.",
        )


def test_approval_is_forbidden_when_component_is_unresolved():
    evidence = _evidence()
    evidence["unresolved_component_ids"] = ["continuous-renewal-exception"]

    with pytest.raises(LiveCertificationReviewError, match="unresolved"):
        build_governed_live_review(
            evidence,
            reviewer_id="reviewer-rajal",
            reviewed_at="2026-08-02T10:30:00+05:30",
            decision=LiveCertificationReviewerDecision.APPROVED_FOR_CERTIFICATION_CONSIDERATION,
            rationale="Approve.",
        )


def test_rework_can_record_non_matching_evidence_without_certification():
    evidence = _evidence()
    evidence["components"][0]["status"] = "MISMATCHED"

    record = build_governed_live_review(
        evidence,
        reviewer_id="reviewer-rajal",
        reviewed_at="2026-08-02T10:30:00+05:30",
        decision=LiveCertificationReviewerDecision.REWORK_REQUIRED,
        rationale="The trigger component must be corrected and rerun.",
    )

    assert record.decision is LiveCertificationReviewerDecision.REWORK_REQUIRED
    assert record.certification_granted is False
