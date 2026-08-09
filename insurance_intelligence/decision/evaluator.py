"""Deterministic finding-level safety evaluation for MO-018C."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping, Sequence

from insurance_intelligence.contracts.decision import (
    ClarificationRequirement,
    FindingDisposition,
    SafetyIssue,
    build_clarification_requirement,
    build_finding_disposition,
    build_safety_issue,
)
from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.reasoning import Finding, ReasoningEngineOutput
from insurance_intelligence.decision.registry import SafetyPolicyDefinition, SafetyPolicyRegistry


class FindingSafetyEvaluationError(ValueError):
    """Raised when finding-level evaluation inputs are invalid."""


@dataclass(frozen=True)
class FindingSafetyEvaluation:
    finding_disposition: FindingDisposition
    safety_issues: tuple[SafetyIssue, ...]
    clarifications: tuple[ClarificationRequirement, ...]
    matched_policy_ids: tuple[str, ...]
    limitations: tuple[str, ...]


def _stable_id(prefix: str, *parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16]}"


def _context_keys(context: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(sorted(str(key) for key, value in context.items() if value is not None))


def _evidence_by_id(output: EvidenceResolverOutput) -> dict[str, object]:
    return {item.evidence_id: item for item in output.evidence_packages}


def _normalise_operation(value: object) -> str:
    text = str(value).strip().upper()
    return "_".join(part for part in "".join(char if char.isalnum() else "_" for char in text).split("_") if part)


def _is_recommendation_operation(value: object) -> bool:
    """Detect explicit and implicit recommendation/suitability operation IDs.

    Pure comparison remains allowed. Selection/ranking/preference signals are
    treated as recommendation-like only when they target a product/policy/plan,
    option, coverage, or fit decision.
    """
    operation = _normalise_operation(value)
    if not operation:
        return False
    tokens = tuple(operation.split("_"))
    token_set = set(tokens)

    if any(token.startswith("RECOMMEND") or token.startswith("SUITAB") for token in tokens):
        return True

    decision_verbs = {"CHOOSE", "SELECT", "PICK", "PREFER", "RANK", "RANKING"}
    has_decision_verb = bool(token_set.intersection(decision_verbs))
    has_decision_target = any(
        token.startswith(("PRODUCT", "PLAN", "POLIC", "OPTION", "COVERAGE"))
        for token in tokens
    )
    if has_decision_verb and has_decision_target:
        return True

    if "BEST" in token_set and (
        "FIT" in token_set or has_decision_target
    ):
        return True

    return False


def _issue(
    *, finding: Finding, issue_type: str, severity: str, policy_id: str,
    description: str, blocking: bool, evidence_ids: Sequence[str] = (),
) -> SafetyIssue:
    return build_safety_issue(
        issue_id=_stable_id("issue", finding.finding_id, policy_id, issue_type),
        issue_type=issue_type,
        severity=severity,
        status="BLOCKING" if blocking else "OPEN",
        description=description,
        policy_id=policy_id,
        finding_ids=(finding.finding_id,),
        evidence_ids=tuple(evidence_ids),
        blocking=blocking,
    )


def _clarification(finding: Finding, key: str, reason: str) -> ClarificationRequirement:
    return build_clarification_requirement(
        clarification_id=_stable_id("clarification", finding.finding_id, key),
        topic="conditional_copayment",
        question_key=key,
        reason=reason,
        priority="HIGH",
        required_context_keys=(key,),
        related_finding_ids=(finding.finding_id,),
    )


def _policy_issue(finding: Finding, policy: SafetyPolicyDefinition) -> SafetyIssue:
    return _issue(
        finding=finding,
        issue_type=policy.issue_type,
        severity=policy.severity,
        policy_id=policy.policy_id,
        description=f"Safety policy {policy.policy_id}@{policy.policy_version} matched the finding.",
        blocking=policy.blocking,
        evidence_ids=finding.evidence_ids,
    )


def evaluate_finding(
    *,
    finding: Finding,
    evidence_resolution: EvidenceResolverOutput,
    reasoning_output: ReasoningEngineOutput,
    policy_registry: SafetyPolicyRegistry,
    domain: str,
    topic: str,
    decision_context: Mapping[str, object] | None = None,
    strict_mode: str = "STRICT",
    requested_operations: Sequence[str] = (),
) -> FindingSafetyEvaluation:
    """Evaluate one reasoning finding without making an aggregate request decision."""
    if not isinstance(finding, Finding):
        raise FindingSafetyEvaluationError("finding must be a validated Finding")
    if not isinstance(evidence_resolution, EvidenceResolverOutput):
        raise FindingSafetyEvaluationError("evidence_resolution must be a validated EvidenceResolverOutput")
    if not isinstance(reasoning_output, ReasoningEngineOutput):
        raise FindingSafetyEvaluationError("reasoning_output must be a validated ReasoningEngineOutput")
    if finding not in reasoning_output.findings:
        raise FindingSafetyEvaluationError("finding must belong to reasoning_output")
    if evidence_resolution.request_id != reasoning_output.request_id:
        raise FindingSafetyEvaluationError("cross-stage request IDs must match")
    if strict_mode not in {"STRICT", "PERMISSIVE"}:
        raise FindingSafetyEvaluationError("strict_mode must be STRICT or PERMISSIVE")

    context = dict(decision_context or {})
    known_evidence = _evidence_by_id(evidence_resolution)
    issues: list[SafetyIssue] = []
    clarifications: list[ClarificationRequirement] = []
    limitations: list[str] = list(finding.limitations)

    missing_ids = tuple(eid for eid in finding.evidence_ids if eid not in known_evidence)
    if missing_ids or not finding.evidence_ids:
        issues.append(_issue(
            finding=finding, issue_type="MISSING_EVIDENCE", severity="CRITICAL",
            policy_id="missing_evidence_fail_closed_v1",
            description="The finding does not preserve resolvable governed evidence.", blocking=True,
            evidence_ids=tuple(eid for eid in finding.evidence_ids if eid in known_evidence),
        ))

    linked = [known_evidence[eid] for eid in finding.evidence_ids if eid in known_evidence]
    bad_lineage = [item.evidence_id for item in linked if item.lineage.lineage_status != "VERIFIED"]
    if bad_lineage or evidence_resolution.sufficiency == "FAILED_LINEAGE":
        issues.append(_issue(
            finding=finding, issue_type="FAILED_LINEAGE", severity="CRITICAL",
            policy_id="failed_lineage_fail_closed_v1",
            description="Required governed evidence lineage is not verified.", blocking=True,
            evidence_ids=bad_lineage,
        ))

    version_unresolved = evidence_resolution.sufficiency == "VERSION_UNRESOLVED" or any(
        item.version_status in {"VERSION_UNRESOLVED", "DATE_UNRESOLVED"} or
        item.applicability_status in {"DATE_UNRESOLVED", "VARIANT_UNRESOLVED"}
        for item in linked
    )
    if version_unresolved:
        issues.append(_issue(
            finding=finding, issue_type="VERSION_UNRESOLVED", severity="HIGH",
            policy_id="version_unresolved_withhold_v1",
            description="The applicable governed document version is unresolved.", blocking=True,
            evidence_ids=finding.evidence_ids,
        ))

    if evidence_resolution.resolution_status in {"NOT_RESOLVED", "INVALID_INPUT"} or evidence_resolution.sufficiency in {"MISSING", "ENTITY_UNRESOLVED"}:
        issue_type = "ENTITY_UNRESOLVED" if evidence_resolution.sufficiency == "ENTITY_UNRESOLVED" else "MISSING_EVIDENCE"
        issues.append(_issue(
            finding=finding, issue_type=issue_type, severity="CRITICAL",
            policy_id="insufficient_evidence_fail_closed_v1",
            description="Evidence resolution is insufficient for communication.", blocking=True,
            evidence_ids=finding.evidence_ids,
        ))

    material_conflicts = [
        conflict for conflict in evidence_resolution.conflicts
        if conflict.materiality.upper() in {"HIGH", "CRITICAL", "MATERIAL"}
        and conflict.resolution_status in {"UNRESOLVED", "REQUIRES_HUMAN_REVIEW", "REQUIRES_POLICY_SCHEDULE"}
        and set(conflict.evidence_ids).intersection(finding.evidence_ids)
    ]
    if material_conflicts or evidence_resolution.resolution_status == "CONFLICTING":
        issues.append(_issue(
            finding=finding, issue_type="MATERIAL_CONFLICT", severity="HIGH",
            policy_id="material_conflict_withhold_v1",
            description="Material governed evidence conflict remains unresolved.", blocking=True,
            evidence_ids=finding.evidence_ids,
        ))

    unsupported = finding.finding_status in {"UNSUPPORTED", "BLOCKED", "CONFLICTING"} or reasoning_output.reasoning_status in {"NOT_REASONED", "CONFLICTING", "INVALID_INPUT"}
    if unsupported:
        issues.append(_issue(
            finding=finding, issue_type="UNSUPPORTED_INFERENCE", severity="HIGH",
            policy_id="unsupported_reasoning_withhold_v1",
            description="The reasoning output does not support communicating this finding.", blocking=True,
            evidence_ids=finding.evidence_ids,
        ))

    assumptions = {item.assumption_id: item for item in reasoning_output.assumptions}
    unapproved = [aid for aid in finding.assumption_ids if aid not in assumptions or assumptions[aid].approval_status not in {"APPROVED_INPUT", "SYSTEM_DEFAULT"}]
    if unapproved:
        issues.append(_issue(
            finding=finding, issue_type="UNAPPROVED_ASSUMPTION", severity="CRITICAL",
            policy_id="unapproved_assumption_fail_closed_v1",
            description="The finding depends on an assumption that was not approved.", blocking=True,
            evidence_ids=finding.evidence_ids,
        ))

    operations = tuple(sorted(set(_normalise_operation(item) for item in requested_operations if str(item).strip())))
    recommendation_ops = tuple(operation for operation in operations if _is_recommendation_operation(operation))
    if recommendation_ops:
        issues.append(_issue(
            finding=finding, issue_type="RECOMMENDATION_WITHOUT_SUITABILITY", severity="CRITICAL",
            policy_id="recommendation_without_suitability_block_v1",
            description=(
                "Recommendation, ranking, selection, preference, or suitability operations are outside "
                "the approved reasoning scope: " + ", ".join(recommendation_ops)
            ),
            blocking=True,
            evidence_ids=finding.evidence_ids,
        ))

    if (finding.finding_status == "CONDITIONAL" or finding.finding_type == "UNRESOLVED_IMPLICATION") and topic == "conditional_copayment" and context.get("trigger_status") is None:
        clarifications.append(_clarification(
            finding, "trigger_status",
            "Case-specific applicability requires the documented co-payment trigger status.",
        ))
        issues.append(_issue(
            finding=finding, issue_type="MISSING_CONTEXT", severity="HIGH",
            policy_id="conditional_copayment_trigger_context_v1",
            description="The conditional co-payment finding cannot be communicated as case-specific without trigger context.",
            blocking=True, evidence_ids=finding.evidence_ids,
        ))

    policies = policy_registry.eligible_policies(
        domain=domain,
        topic=topic,
        finding_type=finding.finding_type,
        finding_status=finding.finding_status,
        derivation_type=finding.derivation_type,
        reasoning_status=reasoning_output.reasoning_status,
        reasoning_sufficiency=reasoning_output.reasoning_sufficiency,
        evidence_resolution_status=evidence_resolution.resolution_status,
        evidence_sufficiency=evidence_resolution.sufficiency,
        strict_mode=strict_mode,
        available_context_keys=_context_keys(context),
        requested_operations=operations,
    )
    for policy in policies:
        issues.append(_policy_issue(finding, policy))

    # Deterministic de-duplication by issue identity.
    unique_issues = {item.issue_id: item for item in issues}
    issues_out = tuple(sorted(unique_issues.values(), key=lambda item: item.issue_id))
    clarifications_out = tuple(sorted(clarifications, key=lambda item: item.clarification_id))
    matched_policy_ids = tuple(sorted({item.policy_id for item in issues_out}))

    blocking = [item for item in issues_out if item.blocking]
    if clarifications_out and all(item.issue_type == "MISSING_CONTEXT" for item in blocking):
        disposition = "WITHHELD_FOR_CLARIFICATION"
        basis = "Required case-specific context is missing."
    elif any(item.issue_type == "RECOMMENDATION_WITHOUT_SUITABILITY" for item in blocking):
        disposition = "BLOCKED"
        basis = "A prohibited recommendation or suitability operation was requested."
    elif any(item.issue_type == "MATERIAL_CONFLICT" for item in blocking):
        disposition = "WITHHELD_CONFLICT"
        basis = "Material evidence conflict remains unresolved."
    elif any(item.issue_type in {"FAILED_LINEAGE", "MISSING_EVIDENCE", "VERSION_UNRESOLVED", "ENTITY_UNRESOLVED"} for item in blocking):
        disposition = "WITHHELD_INSUFFICIENT_EVIDENCE"
        basis = "Governed evidence is insufficient or not safely applicable."
    elif any(item.issue_type in {"UNSUPPORTED_INFERENCE", "UNAPPROVED_ASSUMPTION"} for item in blocking):
        disposition = "WITHHELD_UNSUPPORTED"
        basis = "The finding is not supported for communication."
    elif blocking:
        disposition = "BLOCKED"
        basis = "A blocking safety policy applies."
    elif issues_out or finding.limitations or finding.finding_status in {"SUPPORTED_WITH_LIMITATIONS", "PARTIALLY_SUPPORTED", "CONDITIONAL"}:
        disposition = "APPROVED_WITH_LIMITATIONS"
        basis = "The finding is supported but must retain explicit limitations."
        limitations.append("Communicate only within the documented scope and conditions.")
    else:
        disposition = "APPROVED"
        basis = "The finding is supported by applicable governed evidence."

    approved_evidence_ids = finding.evidence_ids if disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"} else ()
    confidence = finding.confidence
    if blocking:
        confidence = min(confidence, 0.25)
    elif disposition == "APPROVED_WITH_LIMITATIONS":
        confidence = min(confidence, 0.85)

    return FindingSafetyEvaluation(
        finding_disposition=build_finding_disposition(
            finding_id=finding.finding_id,
            disposition=disposition,
            approved_evidence_ids=approved_evidence_ids,
            limitation_ids=tuple(_stable_id("limitation", finding.finding_id, text) for text in sorted(set(limitations))),
            safety_issue_ids=tuple(item.issue_id for item in issues_out),
            clarification_ids=tuple(item.clarification_id for item in clarifications_out),
            basis=basis,
            confidence=confidence,
        ),
        safety_issues=issues_out,
        clarifications=clarifications_out,
        matched_policy_ids=matched_policy_ids,
        limitations=tuple(sorted(set(limitations))),
    )
