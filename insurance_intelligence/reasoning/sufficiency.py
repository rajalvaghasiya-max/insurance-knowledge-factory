"""Deterministic reasoning sufficiency aggregation for MO-017."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.reasoning import RequirementReasoningResult


@dataclass(frozen=True)
class SufficiencyDecision:
    reasoning_sufficiency: str
    reasoning_status: str
    confidence: float
    limitations: tuple[str, ...]


_BLOCKING_STATUSES = frozenset({"BLOCKED_BY_EVIDENCE", "BLOCKED_BY_CONTEXT"})
_LIMITED_STATUSES = frozenset({"SATISFIED_WITH_LIMITATIONS", "PARTIALLY_SATISFIED"})


def evaluate_reasoning_sufficiency(
    requirement_results: Sequence[RequirementReasoningResult],
) -> SufficiencyDecision:
    """Aggregate requirement outcomes using fail-closed deterministic precedence."""
    results = tuple(requirement_results)
    if not results:
        return SufficiencyDecision("UNSUPPORTED", "NO_REASONING_REQUIRED", 0.0, ())

    statuses = {result.status for result in results}
    confidence = _aggregate_confidence(results)
    limitations = _collect_limitations(results)

    if statuses & _BLOCKING_STATUSES:
        return SufficiencyDecision("BLOCKED", "NOT_REASONED", confidence, limitations)
    if "CONFLICTING" in statuses:
        return SufficiencyDecision("CONFLICTING", "CONFLICTING", confidence, limitations)
    if statuses <= {"SATISFIED"}:
        return SufficiencyDecision("COMPLETE", "REASONED", confidence, limitations)
    if statuses <= {"SATISFIED", "SATISFIED_WITH_LIMITATIONS"}:
        return SufficiencyDecision("SUFFICIENT", "REASONED_WITH_LIMITATIONS", confidence, limitations)
    if "CONDITIONAL" in statuses and statuses <= {
        "SATISFIED",
        "SATISFIED_WITH_LIMITATIONS",
        "CONDITIONAL",
    }:
        return SufficiencyDecision("CONDITIONAL", "CONDITIONAL", confidence, limitations)
    if "PARTIALLY_SATISFIED" in statuses:
        return SufficiencyDecision("PARTIAL", "PARTIALLY_REASONED", confidence, limitations)
    if statuses & {"UNSUPPORTED", "NO_APPLICABLE_RULE"}:
        if statuses & {"SATISFIED", "SATISFIED_WITH_LIMITATIONS", "CONDITIONAL"}:
            return SufficiencyDecision("PARTIAL", "PARTIALLY_REASONED", confidence, limitations)
        return SufficiencyDecision("UNSUPPORTED", "NOT_REASONED", confidence, limitations)

    return SufficiencyDecision("UNSUPPORTED", "NOT_REASONED", confidence, limitations)


def _aggregate_confidence(results: Sequence[RequirementReasoningResult]) -> float:
    if not results:
        return 0.0
    raw = sum(result.confidence for result in results) / len(results)
    penalties = {
        "BLOCKED_BY_EVIDENCE": 0.0,
        "BLOCKED_BY_CONTEXT": 0.0,
        "CONFLICTING": 0.25,
        "UNSUPPORTED": 0.25,
        "NO_APPLICABLE_RULE": 0.25,
        "PARTIALLY_SATISFIED": 0.75,
        "CONDITIONAL": 0.85,
        "SATISFIED_WITH_LIMITATIONS": 0.9,
        "SATISFIED": 1.0,
    }
    multiplier = min(penalties[result.status] for result in results)
    return round(max(0.0, min(1.0, raw * multiplier)), 6)


def _collect_limitations(results: Sequence[RequirementReasoningResult]) -> tuple[str, ...]:
    values: list[str] = []
    for result in sorted(results, key=lambda item: item.requirement_id):
        if result.missing_inputs:
            values.append(
                f"{result.requirement_id}: missing inputs: {', '.join(result.missing_inputs)}"
            )
        if result.unsupported_reason:
            values.append(f"{result.requirement_id}: {result.unsupported_reason}")
        if result.status == "CONFLICTING":
            values.append(f"{result.requirement_id}: material reasoning conflict remains")
        if result.status == "BLOCKED_BY_EVIDENCE":
            values.append(f"{result.requirement_id}: reasoning blocked by evidence")
        if result.status == "BLOCKED_BY_CONTEXT":
            values.append(f"{result.requirement_id}: reasoning blocked by approved context")
    return tuple(dict.fromkeys(values))
