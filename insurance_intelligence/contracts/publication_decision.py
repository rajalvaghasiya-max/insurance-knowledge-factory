"""Versioned contracts for governed publication decisions (P2.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.rule_certification import RuleCertificationResult

SUPPORTED_CONTRACT_VERSION = "1.0"
PUBLICATION_DECISION_STATUSES = frozenset({"PUBLISH", "WITHHOLD", "BLOCKED"})
RESOLVABLE_PUBLICATION_BOUNDARIES = frozenset({"bound_not_published"})


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
class PublicationBoundaryAuthorization:
    authorization_id: str
    governed_subject_reference: str
    certification_id: str
    resolved_boundary_tokens: tuple[str, ...]
    authorization_authority: str
    trace_references: tuple[str, ...]


def build_publication_boundary_authorization(
    *,
    authorization_id: str,
    governed_subject_reference: str,
    certification_id: str,
    resolved_boundary_tokens: Sequence[str],
    authorization_authority: str,
    trace_references: Sequence[str],
) -> PublicationBoundaryAuthorization:
    tokens = _unique(resolved_boundary_tokens, "resolved_boundary_tokens")
    if not tokens:
        raise PublicationDecisionContractError("resolved_boundary_tokens must not be empty")
    unsupported = tuple(token for token in tokens if token not in RESOLVABLE_PUBLICATION_BOUNDARIES)
    if unsupported:
        raise PublicationDecisionContractError(
            "unsupported publication boundary token(s): " + ", ".join(unsupported)
        )
    traces = _unique(trace_references, "trace_references")
    if not traces:
        raise PublicationDecisionContractError("trace_references must not be empty")
    return PublicationBoundaryAuthorization(
        authorization_id=_text(authorization_id, "authorization_id"),
        governed_subject_reference=_text(
            governed_subject_reference, "governed_subject_reference"
        ),
        certification_id=_text(certification_id, "certification_id"),
        resolved_boundary_tokens=tokens,
        authorization_authority=_text(authorization_authority, "authorization_authority"),
        trace_references=traces,
    )


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
    boundary_authorization: PublicationBoundaryAuthorization | None = None


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
    boundary_authorization: PublicationBoundaryAuthorization | None = None,
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
    if boundary_authorization is not None:
        if not isinstance(boundary_authorization, PublicationBoundaryAuthorization):
            raise PublicationDecisionContractError(
                "boundary_authorization must be a PublicationBoundaryAuthorization or None"
            )
        if boundary_authorization.governed_subject_reference != subject:
            raise PublicationDecisionContractError(
                "boundary_authorization governed subject must match publication input"
            )
        if boundary_authorization.certification_id != certification_result.certification_id:
            raise PublicationDecisionContractError(
                "boundary_authorization certification id must match certification result"
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
        boundary_authorization=boundary_authorization,
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
    resolved_certification_limitations: tuple[str, ...] = ()
    authorization_id: str | None = None
    authorization_trace_references: tuple[str, ...] = ()


__all__ = [
    "PUBLICATION_DECISION_STATUSES",
    "RESOLVABLE_PUBLICATION_BOUNDARIES",
    "PublicationBoundaryAuthorization",
    "PublicationDecisionContractError",
    "PublicationDecisionInput",
    "PublicationDecisionResult",
    "build_publication_boundary_authorization",
    "build_publication_decision_input",
]
