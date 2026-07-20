"""Deterministic aggregate decision and response-packet policy for MO-018D."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Sequence

from insurance_intelligence.contracts.decision import (
    ApprovedResponsePacket,
    BlockedContent,
    ClarificationRequirement,
    FindingDisposition,
    SafetyIssue,
    build_approved_response_packet,
    build_blocked_content,
)
from insurance_intelligence.decision.evaluator import FindingSafetyEvaluation


class DecisionAggregationError(ValueError):
    """Raised when aggregate decision inputs are invalid."""


@dataclass(frozen=True)
class DecisionAggregation:
    decision: str
    finding_dispositions: tuple[FindingDisposition, ...]
    safety_issues: tuple[SafetyIssue, ...]
    clarifications: tuple[ClarificationRequirement, ...]
    response_packet: ApprovedResponsePacket | None
    blocked_content: tuple[BlockedContent, ...]
    limitations: tuple[str, ...]
    human_review_reasons: tuple[str, ...]
    confidence: float


def _stable_id(prefix: str, *parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16]}"


def _unique_by_id(items: Sequence[object], attr: str) -> tuple[object, ...]:
    by_id = {getattr(item, attr): item for item in items}
    return tuple(by_id[key] for key in sorted(by_id))


def _block_reason(disposition: str, issues: Sequence[SafetyIssue]) -> str:
    issue_types = {item.issue_type for item in issues}
    if "FAILED_LINEAGE" in issue_types:
        return "FAILED_LINEAGE"
    if "MATERIAL_CONFLICT" in issue_types or disposition == "WITHHELD_CONFLICT":
        return "CONFLICTING_EVIDENCE"
    if "MISSING_CONTEXT" in issue_types or disposition in {
        "WITHHELD_FOR_CLARIFICATION", "WITHHELD_INSUFFICIENT_CONTEXT"
    }:
        return "INSUFFICIENT_CONTEXT"
    if "UNAPPROVED_ASSUMPTION" in issue_types:
        return "UNAPPROVED_ASSUMPTION"
    if "RECOMMENDATION_WITHOUT_SUITABILITY" in issue_types or disposition == "BLOCKED":
        return "SAFETY_POLICY"
    if disposition == "WITHHELD_UNSUPPORTED":
        return "UNSUPPORTED_REASONING"
    if disposition == "REFERRED_FOR_HUMAN_REVIEW":
        return "HUMAN_REVIEW_REQUIRED"
    return "INSUFFICIENT_EVIDENCE"


def _decision_for(
    dispositions: Sequence[FindingDisposition],
    issues: Sequence[SafetyIssue],
    clarifications: Sequence[ClarificationRequirement],
    *,
    out_of_scope: bool,
) -> str:
    if out_of_scope:
        return "OUT_OF_SCOPE"
    if not dispositions:
        return "UNSUPPORTED_REASONING"

    values = {item.disposition for item in dispositions}
    issue_types = {item.issue_type for item in issues if item.blocking}
    severities = {item.severity for item in issues if item.blocking}

    if "REFERRED_FOR_HUMAN_REVIEW" in values or "HUMAN_REVIEW_TRIGGER" in issue_types:
        return "HUMAN_REVIEW_REQUIRED"
    if "BLOCKED" in values or "RECOMMENDATION_WITHOUT_SUITABILITY" in issue_types or "CRITICAL" in severities and "SAFETY_POLICY" in {item.policy_id for item in issues}:
        return "BLOCKED"
    if "WITHHELD_CONFLICT" in values or "MATERIAL_CONFLICT" in issue_types:
        return "CONFLICTING_EVIDENCE"
    if "WITHHELD_INSUFFICIENT_EVIDENCE" in values or issue_types.intersection({
        "FAILED_LINEAGE", "VERSION_UNRESOLVED", "ENTITY_UNRESOLVED", "MISSING_EVIDENCE"
    }):
        return "INSUFFICIENT_EVIDENCE"
    if "WITHHELD_UNSUPPORTED" in values or issue_types.intersection({
        "UNSUPPORTED_INFERENCE", "UNAPPROVED_ASSUMPTION"
    }):
        return "UNSUPPORTED_REASONING"
    if "WITHHELD_FOR_CLARIFICATION" in values or any(item.status == "REQUIRED" for item in clarifications):
        return "CLARIFICATION_REQUIRED"
    if "WITHHELD_INSUFFICIENT_CONTEXT" in values or "MISSING_CONTEXT" in issue_types:
        return "INSUFFICIENT_CONTEXT"
    if values <= {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        return "APPROVED_WITH_LIMITATIONS" if "APPROVED_WITH_LIMITATIONS" in values else "APPROVED"
    return "BLOCKED"


def aggregate_decision(
    *,
    request_id: str,
    evaluations: Sequence[FindingSafetyEvaluation],
    prohibited_operations: Sequence[str] = (),
    out_of_scope: bool = False,
) -> DecisionAggregation:
    """Aggregate finding evaluations into one deterministic request-level decision."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise DecisionAggregationError("request_id must be a non-empty string")
    if not isinstance(out_of_scope, bool):
        raise DecisionAggregationError("out_of_scope must be boolean")
    if any(not isinstance(item, FindingSafetyEvaluation) for item in evaluations):
        raise DecisionAggregationError("evaluations must contain FindingSafetyEvaluation values")

    dispositions = tuple(sorted(
        (item.finding_disposition for item in evaluations),
        key=lambda item: item.finding_id,
    ))
    if len({item.finding_id for item in dispositions}) != len(dispositions):
        raise DecisionAggregationError("each finding may be evaluated only once")

    issues = _unique_by_id(
        tuple(issue for item in evaluations for issue in item.safety_issues), "issue_id"
    )
    clarifications = _unique_by_id(
        tuple(clarification for item in evaluations for clarification in item.clarifications),
        "clarification_id",
    )
    limitations = tuple(sorted({text for item in evaluations for text in item.limitations}))

    decision = _decision_for(
        dispositions,
        issues,  # type: ignore[arg-type]
        clarifications,  # type: ignore[arg-type]
        out_of_scope=out_of_scope,
    )

    issue_by_id = {item.issue_id: item for item in issues}
    blocked: list[BlockedContent] = []
    for disposition in dispositions:
        if disposition.disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
            continue
        linked_issues = tuple(
            issue_by_id[issue_id]
            for issue_id in disposition.safety_issue_ids
            if issue_id in issue_by_id
        )
        reason = "OUT_OF_SCOPE" if out_of_scope else _block_reason(disposition.disposition, linked_issues)
        policy_id = linked_issues[0].policy_id if linked_issues else "aggregate_decision_policy_v1"
        blocked.append(build_blocked_content(
            blocked_content_id=_stable_id("blocked", request_id, disposition.finding_id, reason),
            source_type="FINDING",
            source_id=disposition.finding_id,
            reason=reason,
            policy_id=policy_id,
            safety_issue_ids=disposition.safety_issue_ids,
        ))

    response_packet: ApprovedResponsePacket | None = None
    if decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        approved = tuple(
            item for item in dispositions
            if item.disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}
        )
        response_packet = build_approved_response_packet(
            packet_id=_stable_id("packet", request_id, decision, *(item.finding_id for item in approved)),
            approved_finding_ids=tuple(item.finding_id for item in approved),
            approved_evidence_ids=tuple(sorted({
                evidence_id for item in approved for evidence_id in item.approved_evidence_ids
            })),
            limitation_ids=tuple(sorted({
                limitation_id for item in approved for limitation_id in item.limitation_ids
            })),
            clarification_ids=(),
            prohibited_operations=tuple(sorted(set(str(item) for item in prohibited_operations))),
        )

    human_review_reasons = tuple(sorted({
        issue.description for issue in issues
        if issue.issue_type == "HUMAN_REVIEW_TRIGGER" or issue.status == "REFERRED"
    }))
    if decision == "HUMAN_REVIEW_REQUIRED" and not human_review_reasons:
        human_review_reasons = ("A finding requires human review before communication.",)

    confidences = [item.confidence for item in dispositions]
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    caps = {
        "APPROVED": 1.0,
        "APPROVED_WITH_LIMITATIONS": 0.85,
        "CLARIFICATION_REQUIRED": 0.55,
        "INSUFFICIENT_CONTEXT": 0.45,
        "INSUFFICIENT_EVIDENCE": 0.25,
        "CONFLICTING_EVIDENCE": 0.20,
        "UNSUPPORTED_REASONING": 0.20,
        "HUMAN_REVIEW_REQUIRED": 0.20,
        "BLOCKED": 0.10,
        "OUT_OF_SCOPE": 0.0,
    }
    confidence = round(min(confidence, caps[decision]), 6)

    return DecisionAggregation(
        decision=decision,
        finding_dispositions=dispositions,
        safety_issues=issues,  # type: ignore[arg-type]
        clarifications=clarifications,  # type: ignore[arg-type]
        response_packet=response_packet,
        blocked_content=tuple(sorted(blocked, key=lambda item: item.blocked_content_id)),
        limitations=limitations,
        human_review_reasons=human_review_reasons,
        confidence=confidence,
    )
