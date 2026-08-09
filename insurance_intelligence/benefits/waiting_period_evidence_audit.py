"""Registered-source evidence audit for MO-028B waiting-period onboarding.

This module isolates candidate policy-wording pages from an already governed source
registration. It does not approve evidence, publish a product fact, or construct a
WaitingPeriodMechanic. Candidate isolation is intentionally separate from human
review because repeated exclusion markers can occur in base clauses and optional
covers.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Mapping, Any

from insurance_intelligence.benefits.waiting_period_contracts import WaitingPeriodType


class WaitingPeriodEvidenceAuditError(ValueError):
    """Raised when a registered source cannot support deterministic candidate audit."""


class EvidenceAuditStatus(str, Enum):
    NO_CANDIDATE = "NO_CANDIDATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class WaitingPeriodEvidenceCandidate:
    candidate_id: str
    source_page: int
    text_sha256: str
    excerpt: str


@dataclass(frozen=True)
class WaitingPeriodEvidenceAuditResult:
    waiting_period_type: WaitingPeriodType
    marker: str
    status: EvidenceAuditStatus
    document_id: str
    document_version_id: str
    document_sha256: str
    storage_locator: str
    candidates: tuple[WaitingPeriodEvidenceCandidate, ...]


_MARKERS: Mapping[WaitingPeriodType, str] = {
    WaitingPeriodType.PRE_EXISTING_DISEASE: "Code Excl 01",
    WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE: "Code Excl 02",
    WaitingPeriodType.INITIAL: "Code Excl 03",
}


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodEvidenceAuditError(f"{field_name} must be non-empty text")
    return value.strip()


def _required_mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodEvidenceAuditError(f"{field_name} must be an object")
    return value


def load_registered_source(path: str | Path) -> Mapping[str, Any]:
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(f"registered source not found: {source_path}")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WaitingPeriodEvidenceAuditError(
            f"registered source is not valid UTF-8 JSON: {source_path}"
        ) from exc
    return _required_mapping(payload, "registered_source")


def audit_waiting_period_candidates(
    registered_source: Mapping[str, Any],
    waiting_period_type: WaitingPeriodType,
) -> WaitingPeriodEvidenceAuditResult:
    if not isinstance(waiting_period_type, WaitingPeriodType):
        raise WaitingPeriodEvidenceAuditError(
            "waiting_period_type must be a WaitingPeriodType"
        )
    source = _required_mapping(registered_source, "registered_source")
    document = _required_mapping(source.get("document"), "document")
    evidence_review = _required_mapping(source.get("evidence_review"), "evidence_review")
    raw_candidates = evidence_review.get("candidates")
    if not isinstance(raw_candidates, list):
        raise WaitingPeriodEvidenceAuditError("evidence_review.candidates must be an array")

    marker = _MARKERS[waiting_period_type]
    candidates: list[WaitingPeriodEvidenceCandidate] = []
    for index, raw in enumerate(raw_candidates):
        candidate = _required_mapping(raw, f"evidence_review.candidates[{index}]")
        excerpt = _required_text(candidate.get("excerpt"), f"candidate[{index}].excerpt")
        if marker not in excerpt:
            continue
        source_page = candidate.get("source_page")
        if type(source_page) is not int or source_page <= 0:
            raise WaitingPeriodEvidenceAuditError(
                f"candidate[{index}].source_page must be a positive integer"
            )
        candidates.append(
            WaitingPeriodEvidenceCandidate(
                candidate_id=_required_text(
                    candidate.get("candidate_id"), f"candidate[{index}].candidate_id"
                ),
                source_page=source_page,
                text_sha256=_required_text(
                    candidate.get("text_sha256"), f"candidate[{index}].text_sha256"
                ),
                excerpt=excerpt,
            )
        )

    candidates_tuple = tuple(sorted(candidates, key=lambda item: (item.source_page, item.candidate_id)))
    status = (
        EvidenceAuditStatus.REVIEW_REQUIRED
        if candidates_tuple
        else EvidenceAuditStatus.NO_CANDIDATE
    )
    return WaitingPeriodEvidenceAuditResult(
        waiting_period_type=waiting_period_type,
        marker=marker,
        status=status,
        document_id=_required_text(document.get("document_id"), "document.document_id"),
        document_version_id=_required_text(
            document.get("document_version_id"), "document.document_version_id"
        ),
        document_sha256=_required_text(
            document.get("content_sha256"), "document.content_sha256"
        ),
        storage_locator=_required_text(
            document.get("storage_locator"), "document.storage_locator"
        ),
        candidates=candidates_tuple,
    )


def audit_all_waiting_period_candidates(
    registered_source: Mapping[str, Any],
) -> tuple[WaitingPeriodEvidenceAuditResult, ...]:
    return tuple(
        audit_waiting_period_candidates(registered_source, waiting_period_type)
        for waiting_period_type in (
            WaitingPeriodType.INITIAL,
            WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE,
            WaitingPeriodType.PRE_EXISTING_DISEASE,
        )
    )


__all__ = [
    "EvidenceAuditStatus",
    "WaitingPeriodEvidenceAuditError",
    "WaitingPeriodEvidenceAuditResult",
    "WaitingPeriodEvidenceCandidate",
    "audit_all_waiting_period_candidates",
    "audit_waiting_period_candidates",
    "load_registered_source",
]
