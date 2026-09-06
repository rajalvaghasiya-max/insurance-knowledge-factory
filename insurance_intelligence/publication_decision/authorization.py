"""Resolve explicitly authorized publication-state certification boundaries.

This module is topic- and insurer-neutral.  It does not certify evidence or publish
facts.  It evaluates a separate governance authorization against one immutable
certification result and returns effective versus historically-resolved limitations.
"""
from __future__ import annotations

from insurance_intelligence.contracts.publication_decision import (
    PublicationBoundaryAuthorization,
)
from insurance_intelligence.contracts.rule_certification import RuleCertificationResult


class PublicationBoundaryAuthorizationError(ValueError):
    """Raised when a publication-boundary authorization is mismatched."""


def resolve_authorized_certification_limitations(
    *,
    certification: RuleCertificationResult,
    authorization: PublicationBoundaryAuthorization | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return effective and explicitly-resolved certification limitations.

    The certification object is never mutated. Without authorization, every
    certification limitation remains effective. An authorization must match the exact
    governed subject and certification id, and every named token must occur in at least
    one certification limitation.
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
        if any(
            token.casefold() in limitation.casefold()
            for token in authorization.resolved_boundary_tokens
        ):
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
    "PublicationBoundaryAuthorizationError",
    "resolve_authorized_certification_limitations",
]
