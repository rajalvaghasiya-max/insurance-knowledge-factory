"""Versioned contracts for governed authoritative publication (P2.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.publication_decision import PublicationDecisionResult

SUPPORTED_CONTRACT_VERSION = "1.0"
PUBLICATION_STATUS = "AUTHORITATIVE"
SEMANTIC_BASES = frozenset({"ASSERTED", "DERIVED"})


class AuthoritativePublicationContractError(ValueError):
    """Raised when an authoritative-publication contract is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthoritativePublicationContractError(f"{label} must be a non-empty string")
    return value.strip()


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise AuthoritativePublicationContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class GovernedSemanticComponent:
    component_id: str
    status: str
    evidence_references: tuple[str, ...]
    semantic_basis: str = "ASSERTED"
    derivation_references: tuple[str, ...] = ()


def build_governed_semantic_component(
    *,
    component_id: str,
    status: str,
    evidence_references: Sequence[str],
    semantic_basis: str = "ASSERTED",
    derivation_references: Sequence[str] = (),
) -> GovernedSemanticComponent:
    evidence = _unique(evidence_references, "evidence_references")
    if not evidence:
        raise AuthoritativePublicationContractError("evidence_references must not be empty")
    basis = _text(semantic_basis, "semantic_basis")
    if basis not in SEMANTIC_BASES:
        raise AuthoritativePublicationContractError(
            f"semantic_basis must be one of {sorted(SEMANTIC_BASES)}"
        )
    derivations = _unique(derivation_references, "derivation_references")
    if basis == "DERIVED" and not derivations:
        raise AuthoritativePublicationContractError(
            "DERIVED semantic components require derivation_references"
        )
    if basis == "ASSERTED" and derivations:
        raise AuthoritativePublicationContractError(
            "ASSERTED semantic components must not carry derivation_references"
        )
    return GovernedSemanticComponent(
        component_id=_text(component_id, "component_id"),
        status=_text(status, "status"),
        evidence_references=evidence,
        semantic_basis=basis,
        derivation_references=derivations,
    )


@dataclass(frozen=True)
class GovernedPublicationProjection:
    projection_id: str
    governed_subject_reference: str
    certification_id: str
    topic_id: str
    topic_version: str
    semantic_components: tuple[GovernedSemanticComponent, ...]
    limitations: tuple[str, ...]
    evidence_trace_references: tuple[str, ...]
    certification_trace_references: tuple[str, ...]


def build_governed_publication_projection(
    *,
    projection_id: str,
    governed_subject_reference: str,
    certification_id: str,
    topic_id: str,
    topic_version: str,
    semantic_components: Sequence[GovernedSemanticComponent],
    limitations: Sequence[str],
    evidence_trace_references: Sequence[str],
    certification_trace_references: Sequence[str],
) -> GovernedPublicationProjection:
    components = tuple(semantic_components)
    if not components:
        raise AuthoritativePublicationContractError("semantic_components must not be empty")
    if not all(isinstance(item, GovernedSemanticComponent) for item in components):
        raise AuthoritativePublicationContractError(
            "semantic_components must contain GovernedSemanticComponent values"
        )
    ids = [item.component_id for item in components]
    if len(ids) != len(set(ids)):
        raise AuthoritativePublicationContractError("semantic component IDs must be unique")
    evidence_trace = _unique(evidence_trace_references, "evidence_trace_references")
    certification_trace = _unique(
        certification_trace_references, "certification_trace_references"
    )
    if not evidence_trace:
        raise AuthoritativePublicationContractError(
            "evidence_trace_references must not be empty"
        )
    if not certification_trace:
        raise AuthoritativePublicationContractError(
            "certification_trace_references must not be empty"
        )
    return GovernedPublicationProjection(
        projection_id=_text(projection_id, "projection_id"),
        governed_subject_reference=_text(
            governed_subject_reference, "governed_subject_reference"
        ),
        certification_id=_text(certification_id, "certification_id"),
        topic_id=_text(topic_id, "topic_id"),
        topic_version=_text(topic_version, "topic_version"),
        semantic_components=components,
        limitations=_unique(limitations, "limitations"),
        evidence_trace_references=evidence_trace,
        certification_trace_references=certification_trace,
    )


@dataclass(frozen=True)
class AuthoritativePublicationInput:
    contract_version: str
    publication_id: str
    publication_decision: PublicationDecisionResult
    governed_projection: GovernedPublicationProjection
    publication_authority: str


def build_authoritative_publication_input(
    *,
    publication_id: str,
    publication_decision: PublicationDecisionResult,
    governed_projection: GovernedPublicationProjection,
    publication_authority: str,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> AuthoritativePublicationInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise AuthoritativePublicationContractError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    if not isinstance(publication_decision, PublicationDecisionResult):
        raise AuthoritativePublicationContractError(
            "publication_decision must be a PublicationDecisionResult"
        )
    if not isinstance(governed_projection, GovernedPublicationProjection):
        raise AuthoritativePublicationContractError(
            "governed_projection must be a GovernedPublicationProjection"
        )
    return AuthoritativePublicationInput(
        contract_version=contract_version,
        publication_id=_text(publication_id, "publication_id"),
        publication_decision=publication_decision,
        governed_projection=governed_projection,
        publication_authority=_text(publication_authority, "publication_authority"),
    )


@dataclass(frozen=True)
class AuthoritativePublicationRecord:
    contract_version: str
    publication_id: str
    decision_id: str
    governed_subject_reference: str
    certification_id: str
    topic_id: str
    topic_version: str
    publication_status: str
    semantic_components: tuple[GovernedSemanticComponent, ...]
    limitations: tuple[str, ...]
    certification_trace_references: tuple[str, ...]
    evidence_trace_references: tuple[str, ...]
    publication_authority: str
    publication_receipt_id: str
