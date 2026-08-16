"""Generic stale-source detection and source-reverification contract.

This module protects reviewed semantic artifacts from silently surviving a change in
the current governed source version. It does not decide document currentness,
semantic truth, certification, or publication. It only determines whether a prior
review anchor is still current and records the fail-closed disposition of a
reverification result.
"""
from __future__ import annotations

from dataclasses import dataclass


ANCHOR_MATCH = "CURRENT_ANCHOR_MATCH"
REVERIFICATION_REQUIRED = "REVERIFICATION_REQUIRED"

REVERIFICATION_OUTCOMES = frozenset({"CONFIRMED", "DIFFERS", "NOT_PRESENT", "AMBIGUOUS"})

CONTINUE = "CONTINUE"
WITHHELD = "WITHHELD"


class SourceReverificationContractError(ValueError):
    """Raised when source-anchor or reverification input is invalid."""


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise SourceReverificationContractError(f"{label} must be a SHA-256 string")
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise SourceReverificationContractError(
            f"{label} must be a 64-character hexadecimal SHA-256 digest"
        )
    return digest


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceReverificationContractError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class SourceAnchorAssessment:
    reviewed_source_sha256: str
    current_source_sha256: str
    anchor_status: str
    flow_state: str
    withhold_reason: str | None


@dataclass(frozen=True)
class SourceReverificationResult:
    reviewed_source_sha256: str
    current_source_sha256: str
    outcome: str
    evidence_reference: str
    flow_state: str
    withhold_reason: str | None
    prior_semantic_fact_reusable: bool


def assess_source_anchor(
    *,
    reviewed_source_sha256: str,
    current_source_sha256: str,
) -> SourceAnchorAssessment:
    """Compare a reviewed semantic artifact's source anchor to the current source.

    A mismatch is a positive, auditable withhold state. It is never treated as a
    warning and never permits the prior semantic fact to continue toward
    certification/publication without reverification.
    """
    reviewed = _sha256(reviewed_source_sha256, "reviewed_source_sha256")
    current = _sha256(current_source_sha256, "current_source_sha256")
    if reviewed == current:
        return SourceAnchorAssessment(
            reviewed_source_sha256=reviewed,
            current_source_sha256=current,
            anchor_status=ANCHOR_MATCH,
            flow_state=CONTINUE,
            withhold_reason=None,
        )
    return SourceAnchorAssessment(
        reviewed_source_sha256=reviewed,
        current_source_sha256=current,
        anchor_status=REVERIFICATION_REQUIRED,
        flow_state=WITHHELD,
        withhold_reason="source_reverification_required",
    )


def record_source_reverification(
    *,
    anchor: SourceAnchorAssessment,
    outcome: str,
    evidence_reference: str,
) -> SourceReverificationResult:
    """Record the current-source result for a stale reviewed semantic artifact.

    Only CONFIRMED allows the prior semantic proposition to continue unchanged.
    DIFFERS means the current source establishes different semantics and therefore
    requires a fresh semantic review; NOT_PRESENT and AMBIGUOUS remain withheld.
    """
    if not isinstance(anchor, SourceAnchorAssessment):
        raise SourceReverificationContractError("anchor must be a SourceAnchorAssessment")
    if anchor.anchor_status != REVERIFICATION_REQUIRED:
        raise SourceReverificationContractError(
            "reverification may only be recorded for REVERIFICATION_REQUIRED anchors"
        )
    normalized_outcome = _text(outcome, "outcome").upper()
    if normalized_outcome not in REVERIFICATION_OUTCOMES:
        raise SourceReverificationContractError(
            f"outcome must be one of {sorted(REVERIFICATION_OUTCOMES)}; got {normalized_outcome!r}"
        )
    reference = _text(evidence_reference, "evidence_reference")

    if normalized_outcome == "CONFIRMED":
        return SourceReverificationResult(
            reviewed_source_sha256=anchor.reviewed_source_sha256,
            current_source_sha256=anchor.current_source_sha256,
            outcome=normalized_outcome,
            evidence_reference=reference,
            flow_state=CONTINUE,
            withhold_reason=None,
            prior_semantic_fact_reusable=True,
        )

    reason_by_outcome = {
        "DIFFERS": "current_source_differs_semantic_review_required",
        "NOT_PRESENT": "current_source_proposition_not_present",
        "AMBIGUOUS": "current_source_reverification_ambiguous",
    }
    return SourceReverificationResult(
        reviewed_source_sha256=anchor.reviewed_source_sha256,
        current_source_sha256=anchor.current_source_sha256,
        outcome=normalized_outcome,
        evidence_reference=reference,
        flow_state=WITHHELD,
        withhold_reason=reason_by_outcome[normalized_outcome],
        prior_semantic_fact_reusable=False,
    )


__all__ = [
    "ANCHOR_MATCH",
    "CONTINUE",
    "REVERIFICATION_OUTCOMES",
    "REVERIFICATION_REQUIRED",
    "WITHHELD",
    "SourceAnchorAssessment",
    "SourceReverificationContractError",
    "SourceReverificationResult",
    "assess_source_anchor",
    "record_source_reverification",
]
