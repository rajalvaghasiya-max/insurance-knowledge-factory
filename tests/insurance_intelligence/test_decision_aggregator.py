from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.decision import (
    build_clarification_requirement,
    build_finding_disposition,
    build_safety_issue,
)
from insurance_intelligence.decision.aggregator import (
    DecisionAggregationError,
    aggregate_decision,
)
from insurance_intelligence.decision.evaluator import FindingSafetyEvaluation


def evaluation(
    finding_id="finding-1",
    *,
    disposition="APPROVED",
    issue_type=None,
    severity="HIGH",
    blocking=False,
    clarification=False,
    limitations=(),
    confidence=0.9,
):
    issue = ()
    issue_ids = ()
    if issue_type:
        built = build_safety_issue(
            issue_id=f"issue-{finding_id}-{issue_type}",
            issue_type=issue_type,
            severity=severity,
            status="BLOCKING" if blocking else "OPEN",
            description=f"{issue_type} issue",
            policy_id=f"policy-{issue_type}",
            finding_ids=(finding_id,),
            evidence_ids=("ev-1",),
            blocking=blocking,
        )
        issue = (built,)
        issue_ids = (built.issue_id,)
    clarifications = ()
    clarification_ids = ()
    if clarification:
        built_clarification = build_clarification_requirement(
            clarification_id=f"clarification-{finding_id}",
            topic="conditional_copayment",
            question_key="trigger_status",
            reason="Trigger status is required.",
            priority="HIGH",
            required_context_keys=("trigger_status",),
            related_finding_ids=(finding_id,),
        )
        clarifications = (built_clarification,)
        clarification_ids = (built_clarification.clarification_id,)
    approved_evidence = ("ev-1",) if disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"} else ()
    finding_disposition = build_finding_disposition(
        finding_id=finding_id,
        disposition=disposition,
        approved_evidence_ids=approved_evidence,
        limitation_ids=(f"lim-{finding_id}",) if limitations else (),
        safety_issue_ids=issue_ids,
        clarification_ids=clarification_ids,
        basis="deterministic test basis",
        confidence=confidence,
    )
    return FindingSafetyEvaluation(
        finding_disposition=finding_disposition,
        safety_issues=issue,
        clarifications=clarifications,
        matched_policy_ids=tuple(item.policy_id for item in issue),
        limitations=tuple(limitations),
    )


def test_all_approved_produces_response_packet():
    result = aggregate_decision(request_id="req", evaluations=(evaluation(),))
    assert result.decision == "APPROVED"
    assert result.response_packet is not None
    assert result.response_packet.approved_finding_ids == ("finding-1",)
    assert result.response_packet.approved_evidence_ids == ("ev-1",)


def test_approved_with_limitations_preserves_limitations_and_packet():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation(disposition="APPROVED_WITH_LIMITATIONS", limitations=("Keep condition explicit.",)),),
    )
    assert result.decision == "APPROVED_WITH_LIMITATIONS"
    assert result.limitations == ("Keep condition explicit.",)
    assert result.response_packet is not None
    assert result.response_packet.limitation_ids == ("lim-finding-1",)


def test_clarification_required_prevents_response_packet():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation(
            disposition="WITHHELD_FOR_CLARIFICATION",
            issue_type="MISSING_CONTEXT",
            blocking=True,
            clarification=True,
        ),),
    )
    assert result.decision == "CLARIFICATION_REQUIRED"
    assert result.response_packet is None
    assert result.clarifications[0].required_context_keys == ("trigger_status",)


def test_insufficient_evidence_precedes_clarification():
    results = (
        evaluation(
            "finding-1", disposition="WITHHELD_FOR_CLARIFICATION",
            issue_type="MISSING_CONTEXT", blocking=True, clarification=True,
        ),
        evaluation(
            "finding-2", disposition="WITHHELD_INSUFFICIENT_EVIDENCE",
            issue_type="FAILED_LINEAGE", severity="CRITICAL", blocking=True,
        ),
    )
    assert aggregate_decision(request_id="req", evaluations=results).decision == "INSUFFICIENT_EVIDENCE"


def test_material_conflict_precedes_insufficient_evidence():
    results = (
        evaluation("finding-1", disposition="WITHHELD_CONFLICT", issue_type="MATERIAL_CONFLICT", blocking=True),
        evaluation("finding-2", disposition="WITHHELD_INSUFFICIENT_EVIDENCE", issue_type="MISSING_EVIDENCE", blocking=True),
    )
    assert aggregate_decision(request_id="req", evaluations=results).decision == "CONFLICTING_EVIDENCE"


def test_unsupported_reasoning_is_reported():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation(
            disposition="WITHHELD_UNSUPPORTED",
            issue_type="UNSUPPORTED_INFERENCE",
            blocking=True,
        ),),
    )
    assert result.decision == "UNSUPPORTED_REASONING"
    assert result.blocked_content[0].reason == "UNSUPPORTED_REASONING"


def test_recommendation_operation_is_blocked():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation(
            disposition="BLOCKED",
            issue_type="RECOMMENDATION_WITHOUT_SUITABILITY",
            severity="CRITICAL",
            blocking=True,
        ),),
    )
    assert result.decision == "BLOCKED"
    assert result.confidence <= 0.1


def test_human_review_has_reason():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation(
            disposition="REFERRED_FOR_HUMAN_REVIEW",
            issue_type="HUMAN_REVIEW_TRIGGER",
            blocking=True,
        ),),
    )
    assert result.decision == "HUMAN_REVIEW_REQUIRED"
    assert result.human_review_reasons


def test_out_of_scope_overrides_all_findings():
    result = aggregate_decision(request_id="req", evaluations=(evaluation(),), out_of_scope=True)
    assert result.decision == "OUT_OF_SCOPE"
    assert result.response_packet is None
    assert result.confidence == 0.0


def test_no_evaluations_is_unsupported_and_deterministic():
    first = aggregate_decision(request_id="req", evaluations=())
    second = aggregate_decision(request_id="req", evaluations=())
    assert first == second
    assert first.decision == "UNSUPPORTED_REASONING"


def test_mixed_approved_and_withheld_does_not_leak_packet():
    result = aggregate_decision(
        request_id="req",
        evaluations=(
            evaluation("finding-a"),
            evaluation("finding-b", disposition="WITHHELD_INSUFFICIENT_EVIDENCE", issue_type="MISSING_EVIDENCE", blocking=True),
        ),
    )
    assert result.decision == "INSUFFICIENT_EVIDENCE"
    assert result.response_packet is None


def test_blocked_content_is_created_for_every_withheld_finding():
    result = aggregate_decision(
        request_id="req",
        evaluations=(
            evaluation("finding-b", disposition="WITHHELD_UNSUPPORTED", issue_type="UNSUPPORTED_INFERENCE", blocking=True),
            evaluation("finding-a", disposition="WITHHELD_CONFLICT", issue_type="MATERIAL_CONFLICT", blocking=True),
        ),
    )
    assert {item.source_id for item in result.blocked_content} == {"finding-a", "finding-b"}


def test_failed_lineage_maps_to_failed_lineage_block_reason():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation(
            disposition="WITHHELD_INSUFFICIENT_EVIDENCE",
            issue_type="FAILED_LINEAGE",
            severity="CRITICAL",
            blocking=True,
        ),),
    )
    assert result.blocked_content[0].reason == "FAILED_LINEAGE"


def test_response_packet_deduplicates_evidence_and_operations():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation("finding-b"), evaluation("finding-a")),
        prohibited_operations=("RECOMMEND_PRODUCT", "RECOMMEND_PRODUCT"),
    )
    assert result.response_packet is not None
    assert result.response_packet.approved_finding_ids == ("finding-a", "finding-b")
    assert result.response_packet.approved_evidence_ids == ("ev-1",)
    assert result.response_packet.prohibited_operations == ("RECOMMEND_PRODUCT",)


def test_input_order_does_not_change_output():
    a = evaluation("finding-a")
    b = evaluation("finding-b", disposition="APPROVED_WITH_LIMITATIONS", limitations=("Limit",))
    first = aggregate_decision(request_id="req", evaluations=(a, b))
    second = aggregate_decision(request_id="req", evaluations=(b, a))
    assert first == second


def test_duplicate_finding_evaluation_is_rejected():
    item = evaluation("finding-1")
    with pytest.raises(DecisionAggregationError, match="only once"):
        aggregate_decision(request_id="req", evaluations=(item, item))


def test_invalid_request_id_is_rejected():
    with pytest.raises(DecisionAggregationError, match="request_id"):
        aggregate_decision(request_id="", evaluations=())


def test_invalid_evaluation_type_is_rejected():
    with pytest.raises(DecisionAggregationError, match="FindingSafetyEvaluation"):
        aggregate_decision(request_id="req", evaluations=(object(),))


def test_confidence_is_capped_by_decision():
    result = aggregate_decision(
        request_id="req",
        evaluations=(evaluation(
            disposition="WITHHELD_INSUFFICIENT_EVIDENCE",
            issue_type="MISSING_EVIDENCE",
            blocking=True,
            confidence=1.0,
        ),),
    )
    assert result.confidence == 0.25


def test_aggregate_output_is_immutable():
    result = aggregate_decision(request_id="req", evaluations=(evaluation(),))
    with pytest.raises(Exception):
        result.decision = "BLOCKED"


def test_evaluations_are_not_mutated():
    item = evaluation()
    before = replace(item)
    aggregate_decision(request_id="req", evaluations=(item,))
    assert item == before
