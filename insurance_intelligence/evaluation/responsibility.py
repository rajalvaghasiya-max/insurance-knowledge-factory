"""Bounded LLM responsibility decision reporting for MO-022F.8.

This module aggregates controlled-evaluation evidence into reviewable decisions.
It does not authorize production use, enable a responsibility, or mutate any
underlying deterministic or external evaluation result.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from insurance_intelligence.contracts.llm_evaluation import (
    DeterministicEvaluationResult,
    EvaluationCase,
    EvaluationDisagreement,
    EvaluationDisagreementCategory,
    EvaluationVerdict,
    LLMResponsibility,
    ResponsibilityDecision,
    ResponsibilityDecisionStatus,
)


class ResponsibilityDecisionError(ValueError):
    """Raised when responsibility-report inputs violate evidence invariants."""


@dataclass(frozen=True)
class ResponsibilityEvidence:
    """One controlled case and its immutable evaluation evidence."""

    case: EvaluationCase
    deterministic_result: DeterministicEvaluationResult
    disagreements: tuple[EvaluationDisagreement, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.case, EvaluationCase):
            raise ResponsibilityDecisionError("case must be an EvaluationCase")
        if not isinstance(self.deterministic_result, DeterministicEvaluationResult):
            raise ResponsibilityDecisionError(
                "deterministic_result must be a DeterministicEvaluationResult"
            )
        if not isinstance(self.disagreements, tuple):
            raise ResponsibilityDecisionError("disagreements must be a tuple")
        if not all(
            isinstance(item, EvaluationDisagreement) for item in self.disagreements
        ):
            raise ResponsibilityDecisionError(
                "disagreements must contain EvaluationDisagreement values"
            )
        if self.case.case_id != self.deterministic_result.case_id:
            raise ResponsibilityDecisionError(
                "case and deterministic result case_id values must match"
            )
        if any(item.case_id != self.case.case_id for item in self.disagreements):
            raise ResponsibilityDecisionError(
                "all disagreements must match the evidence case_id"
            )
        if any(
            item.trace_id != self.deterministic_result.trace_id
            for item in self.disagreements
        ):
            raise ResponsibilityDecisionError(
                "all disagreements must match the deterministic trace_id"
            )
        ids = tuple(item.disagreement_id for item in self.disagreements)
        if len(set(ids)) != len(ids):
            raise ResponsibilityDecisionError(
                "disagreements must have unique disagreement IDs"
            )


def _decision_id(
    responsibility: LLMResponsibility,
    evidence_case_ids: tuple[str, ...],
    status: ResponsibilityDecisionStatus,
) -> str:
    payload = "|".join(
        (responsibility.value, status.value, *evidence_case_ids)
    )
    return f"responsibility_{sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _has_external_conflict(evidence: ResponsibilityEvidence) -> bool:
    return any(
        item.category
        in {
            EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS,
            EvaluationDisagreementCategory.DETERMINISTIC_PASS_EXTERNAL_FAIL,
        }
        for item in evidence.disagreements
    )


def _has_inconclusive_external_evidence(evidence: ResponsibilityEvidence) -> bool:
    return any(
        item.category is EvaluationDisagreementCategory.INCONCLUSIVE
        or item.review_required
        for item in evidence.disagreements
    )


def _classify(
    evidence_items: tuple[ResponsibilityEvidence, ...],
) -> ResponsibilityDecisionStatus:
    verdicts = tuple(item.deterministic_result.verdict for item in evidence_items)

    if not evidence_items:
        return ResponsibilityDecisionStatus.INSUFFICIENT_EVIDENCE

    if any(verdict is EvaluationVerdict.FAILED for verdict in verdicts):
        return ResponsibilityDecisionStatus.REJECTED

    if any(
        verdict in {
            EvaluationVerdict.NOT_EVALUATED,
            EvaluationVerdict.REQUIRES_REVIEW,
        }
        for verdict in verdicts
    ):
        return ResponsibilityDecisionStatus.INSUFFICIENT_EVIDENCE

    if any(_has_external_conflict(item) for item in evidence_items):
        return ResponsibilityDecisionStatus.EXPERIMENTAL_ONLY

    if any(
        _has_inconclusive_external_evidence(item) for item in evidence_items
    ):
        return ResponsibilityDecisionStatus.EXPERIMENTAL_ONLY

    if any(
        item.deterministic_result.limitations
        for item in evidence_items
    ):
        return ResponsibilityDecisionStatus.APPROVED_WITH_DETERMINISTIC_VALIDATION

    return ResponsibilityDecisionStatus.APPROVED_FOR_CONTROLLED_USE


def _required_controls(
    evidence_items: tuple[ResponsibilityEvidence, ...],
    status: ResponsibilityDecisionStatus,
) -> tuple[str, ...]:
    if status is not ResponsibilityDecisionStatus.APPROVED_WITH_DETERMINISTIC_VALIDATION:
        return ()
    controls = {
        limitation
        for item in evidence_items
        for limitation in item.deterministic_result.limitations
    }
    controls.add("Retain deterministic validation as the authoritative acceptance gate.")
    return tuple(sorted(controls))


def _rationale(
    *,
    responsibility: LLMResponsibility,
    evidence_items: tuple[ResponsibilityEvidence, ...],
    status: ResponsibilityDecisionStatus,
) -> tuple[str, ...]:
    verdict_counts = {
        verdict: sum(
            item.deterministic_result.verdict is verdict
            for item in evidence_items
        )
        for verdict in EvaluationVerdict
    }
    conflict_count = sum(_has_external_conflict(item) for item in evidence_items)
    inconclusive_count = sum(
        _has_inconclusive_external_evidence(item) for item in evidence_items
    )
    return (
        (
            f"Responsibility {responsibility.value} was reviewed using "
            f"{len(evidence_items)} controlled evaluation case(s)."
        ),
        (
            "Deterministic verdicts: "
            + ", ".join(
                f"{verdict.value}={verdict_counts[verdict]}"
                for verdict in EvaluationVerdict
            )
            + "."
        ),
        (
            f"External comparison signals: conflicts={conflict_count}, "
            f"inconclusive_or_review={inconclusive_count}."
        ),
        f"Bounded decision status: {status.value}.",
        (
            "This report is controlled-evaluation evidence only and does not "
            "authorize production use or enable the responsibility."
        ),
    )


def build_responsibility_decision(
    *,
    responsibility: LLMResponsibility,
    evidence_items: tuple[ResponsibilityEvidence, ...],
) -> ResponsibilityDecision:
    """Build one conservative responsibility decision from controlled evidence."""
    if not isinstance(responsibility, LLMResponsibility):
        raise ResponsibilityDecisionError(
            "responsibility must be an LLMResponsibility"
        )
    if not isinstance(evidence_items, tuple):
        raise ResponsibilityDecisionError("evidence_items must be a tuple")
    if not all(
        isinstance(item, ResponsibilityEvidence) for item in evidence_items
    ):
        raise ResponsibilityDecisionError(
            "evidence_items must contain ResponsibilityEvidence values"
        )
    if any(
        item.case.responsibility is not responsibility
        for item in evidence_items
    ):
        raise ResponsibilityDecisionError(
            "all evidence cases must match the requested responsibility"
        )

    if not evidence_items:
        raise ResponsibilityDecisionError(
            "at least one evidence item is required for a reviewed responsibility"
        )

    case_ids = tuple(sorted(item.case.case_id for item in evidence_items))
    if len(set(case_ids)) != len(case_ids):
        raise ResponsibilityDecisionError(
            "evidence_items must have unique case IDs"
        )

    ordered = tuple(sorted(evidence_items, key=lambda item: item.case.case_id))
    status = _classify(ordered)
    controls = _required_controls(ordered, status)
    return ResponsibilityDecision(
        decision_id=_decision_id(responsibility, case_ids, status),
        responsibility=responsibility,
        status=status,
        rationale=_rationale(
            responsibility=responsibility,
            evidence_items=ordered,
            status=status,
        ),
        evidence_case_ids=case_ids,
        required_controls=controls,
    )


def build_responsibility_decision_report(
    *,
    responsibilities: tuple[LLMResponsibility, ...],
    evidence_items: tuple[ResponsibilityEvidence, ...],
) -> tuple[ResponsibilityDecision, ...]:
    """Return one decision per requested responsibility in deterministic order."""
    if not isinstance(responsibilities, tuple):
        raise ResponsibilityDecisionError("responsibilities must be a tuple")
    if not all(
        isinstance(item, LLMResponsibility) for item in responsibilities
    ):
        raise ResponsibilityDecisionError(
            "responsibilities must contain LLMResponsibility values"
        )
    if len(set(responsibilities)) != len(responsibilities):
        raise ResponsibilityDecisionError(
            "responsibilities must not contain duplicates"
        )
    if not isinstance(evidence_items, tuple):
        raise ResponsibilityDecisionError("evidence_items must be a tuple")
    if not all(
        isinstance(item, ResponsibilityEvidence) for item in evidence_items
    ):
        raise ResponsibilityDecisionError(
            "evidence_items must contain ResponsibilityEvidence values"
        )

    decisions = []
    for responsibility in sorted(
        responsibilities,
        key=lambda item: item.value,
    ):
        matching = tuple(
            item
            for item in evidence_items
            if item.case.responsibility is responsibility
        )
        if not matching:
            continue
        decisions.append(
            build_responsibility_decision(
                responsibility=responsibility,
                evidence_items=matching,
            )
        )
    return tuple(decisions)
