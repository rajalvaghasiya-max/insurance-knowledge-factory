"""Versioned contracts for governed publication decisions (P2.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.rule_certification import RuleCertificationResult

SUPPORTED_CONTRACT_VERSION = "1.0"
PUBLICATION_DECISION_STATUSES = frozenset({"PUBLISH", "WITHHOLD", "BLOCKED"})


class PublicationDecisionContractError(ValueError):
    """Raised when a publication-decision contract is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationDecisionContractError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise PublicationDecisionContractError(
            f"{label} must be one of {sorted(allowed)}; got {value!r}"
        )
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise PublicationDecisionContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class PublicationDecisionInput:
    contract_version: str
    decision_id: str
    governed_subject_reference: str
    certification_result: RuleCertificationResult
    requested_status: str
    decision_reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_trace_references: tuple[str, ...]
    decision_authority: str


def build_publication_decision_input(
    *,
    decision_id: str,
    governed_subject_reference: str,
    certification_result: RuleCertificationResult,
    requested_status: str,
    decision_reasons: Sequence[str],
    limitations: Sequence[str],
    evidence_trace_references: Sequence[str],
    decision_authority: str,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> PublicationDecisionInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise PublicationDecisionContractError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    if not isinstance(certification_result, RuleCertificationResult):
        raise PublicationDecisionContractError(
            "certification_result must be a RuleCertificationResult"
        )
    subject = _text(governed_subject_reference, "governed_subject_reference")
    if subject != certification_result.governed_subject_reference:
        raise PublicationDecisionContractError(
            "governed_subject_reference must match certification_result"
        )
    reasons = _unique(decision_reasons, "decision_reasons")
    if not reasons:
        raise PublicationDecisionContractError("decision_reasons must not be empty")
    return PublicationDecisionInput(
        contract_version=contract_version,
        decision_id=_text(decision_id, "decision_id"),
        governed_subject_reference=subject,
        certification_result=certification_result,
        requested_status=_member(
            requested_status,
            PUBLICATION_DECISION_STATUSES,
            "requested_status",
        ),
        decision_reasons=reasons,
        limitations=_unique(limitations, "limitations"),
        evidence_trace_references=_unique(
            evidence_trace_references,
            "evidence_trace_references",
        ),
        decision_authority=_text(decision_authority, "decision_authority"),
    )


@dataclass(frozen=True)
class PublicationDecisionResult:
    contract_version: str
    decision_id: str
    governed_subject_reference: str
    certification_id: str
    certification_outcome: str
    topic_id: str
    topic_version: str
    requested_status: str
    decision_status: str
    decision_reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    certification_trace_references: tuple[str, ...]
    evidence_trace_references: tuple[str, ...]
    decision_authority: str
    publication_permitted: bool
    authoritative_publication_created: bool
    failures: tuple[str, ...]
