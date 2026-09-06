"""Explicit authorization for resolving publication-state certification boundaries.

This module is topic- and insurer-neutral.  It does not certify evidence or publish
facts.  It records a separate governance authority that may resolve only explicitly
supported publication-state limitations while preserving the historical certification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.rule_certification import RuleCertificationResult

RESOLVABLE_PUBLICATION_BOUNDARIES = frozenset({"bound_not_published"})


class PublicationBoundaryAuthorizationError(ValueError):
    """Raised when a publication-boundary authorization is invalid or mismatched."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationBoundaryAuthorizationError(f"{label} must be non-empty text")
    return value.strip()


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    cleaned = tuple(_text(value, f"{label}[]") for value in values)
    if not cleaned:
        raise PublicationBoundaryAuthorizationError(f"{label} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise PublicationBoundaryAuthorizationError(f"{label} must not contain duplicates")
    return cleaned


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
    unsupported = tuple(token for token in tokens if token not in RESOLVABLE_PUBLICATION_BOUNDARIES)
    if unsupported:
        raise PublicationBoundaryAuthorizationError(
            "unsupported publication boundary token(s): " + ", ".join(unsupported)
        )
    return PublicationBoundaryAuthorization(
        authorization_id=_text(authorization_id, "authorization_id"),
        governed_subject_reference=_text(
            governed_subject_reference, "governed_subject_reference"
        ),
        certification_id=_text(certification_id, "certification_id"),
        resolved_boundary_tokens=tokens,
        authorization_authority=_text(authorization_authority, "authorization_authority"),
        trace_references=_unique(trace_references, "trace_references"),
    )


def resolve_authorized_certification_limitations(
    *,
    certification: RuleCertificationResult,
    authorization: PublicationBoundaryAuthorization | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return effective and explicitly-resolved certification limitations.

    The certification object is never mutated.  Without authorization, every
    certification limitation remains effective.  An authorization must match the exact
    governed subject and certification id, and every named token must actually occur in
    at least one certification limitation.
    """
    if not isinstance(certification, RuleCertificationResult):
        raise PublicationBoundaryAuthorizationError(
            "certification must be a RuleCertificationResult"
        )
    if authorization is None:
        return certification.limitations, ()
    if not isinstance(authorization, PublicationBoundaryAuthorization):
        raise PublicationBoundaryAuthorizationError(
            "authorization must be a PublicationBoundaryAuthorization or None"
        )
    if authorization.governed_subject_reference != certification.governed_subject_reference:
        raise PublicationBoundaryAuthorizationError(
            "authorization governed subject does not match certification"
        )
    if authorization.certification_id != certification.certification_id:
        raise PublicationBoundaryAuthorizationError(
            "authorization certification id does not match certification"
        )

    resolved: list[str] = []
    effective: list[str] = []
    for limitation in certification.limitations:
        if any(token.casefold() in limitation.casefold() for token in authorization.resolved_boundary_tokens):
            resolved.append(limitation)
        else:
            effective.append(limitation)

    for token in authorization.resolved_boundary_tokens:
        if not any(token.casefold() in limitation.casefold() for limitation in resolved):
            raise PublicationBoundaryAuthorizationError(
                f"authorized boundary token is absent from certification limitations: {token}"
            )
    return tuple(effective), tuple(resolved)


__all__ = [
    "PublicationBoundaryAuthorization",
    "PublicationBoundaryAuthorizationError",
    "RESOLVABLE_PUBLICATION_BOUNDARIES",
    "build_publication_boundary_authorization",
    "resolve_authorized_certification_limitations",
]
