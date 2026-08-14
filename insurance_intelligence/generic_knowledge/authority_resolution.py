"""Generic source-authority and regulatory-overlay resolution for MO-028B.G2.

This module is product-agnostic. It resolves competing evidence by governed authority class,
respects effective-date applicability, keeps regulatory overlays distinct from contract facts,
and fails closed on unresolved equal-authority contradictions. It must never branch on insurer
or product identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Mapping, Sequence

from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    GenericKnowledgeContractError,
    PublicationBlocker,
    PublicationBlockerCode,
)


class AuthorityResolutionError(GenericKnowledgeContractError):
    """Raised when authority-resolution inputs are invalid."""


class AuthorityClass(str, Enum):
    REGULATORY_OVERLAY = "REGULATORY_OVERLAY"
    POLICY_WORDING = "POLICY_WORDING"
    CUSTOMER_INFORMATION_SHEET = "CUSTOMER_INFORMATION_SHEET"
    PROSPECTUS = "PROSPECTUS"
    BROCHURE = "BROCHURE"
    WEBPAGE = "WEBPAGE"
    MARKETING = "MARKETING"


class AuthorityResolutionStatus(str, Enum):
    """Outcome of source-authority selection, distinct from semantic readiness status."""

    RESOLVED = "RESOLVED"
    CONFLICTED = "CONFLICTED"
    NO_APPLICABLE_CANDIDATE = "NO_APPLICABLE_CANDIDATE"


# Transitional compatibility for pre-AR-2.4 callers. New code must import
# AuthorityResolutionStatus so authority selection cannot be confused with the semantic
# readiness ResolutionStatus lattice. This alias is deliberately omitted from __all__.
ResolutionStatus = AuthorityResolutionStatus


_AUTHORITY_RANK: Mapping[AuthorityClass, int] = {
    AuthorityClass.REGULATORY_OVERLAY: 700,
    AuthorityClass.POLICY_WORDING: 600,
    AuthorityClass.CUSTOMER_INFORMATION_SHEET: 500,
    AuthorityClass.PROSPECTUS: 400,
    AuthorityClass.BROCHURE: 300,
    AuthorityClass.WEBPAGE: 200,
    AuthorityClass.MARKETING: 100,
}


@dataclass(frozen=True)
class AuthorityCandidate:
    candidate_id: str
    concept: str
    semantic_key: str
    semantic_value: Mapping[str, Any]
    applicability: ApplicabilityKey
    evidence: EvidenceReference
    authority_class: AuthorityClass
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        for field_name in ("candidate_id", "concept", "semantic_key"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise AuthorityResolutionError(f"{field_name} must be non-empty text")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.semantic_value, Mapping) or not self.semantic_value:
            raise AuthorityResolutionError("semantic_value must be a non-empty mapping")
        if not isinstance(self.applicability, ApplicabilityKey):
            raise AuthorityResolutionError("applicability must be an ApplicabilityKey")
        if not isinstance(self.evidence, EvidenceReference):
            raise AuthorityResolutionError("evidence must be an EvidenceReference")
        if not isinstance(self.authority_class, AuthorityClass):
            raise AuthorityResolutionError("authority_class must be an AuthorityClass")
        if self.evidence.authority_class != self.authority_class.value:
            raise AuthorityResolutionError(
                "evidence.authority_class must match authority_class"
            )
        if self.effective_from is not None and not isinstance(self.effective_from, date):
            raise AuthorityResolutionError("effective_from must be a date")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise AuthorityResolutionError("effective_to must be a date")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise AuthorityResolutionError("effective_to cannot precede effective_from")


@dataclass(frozen=True)
class AuthorityResolution:
    status: AuthorityResolutionStatus
    concept: str
    semantic_key: str
    as_of_date: date
    selected_candidate_ids: tuple[str, ...]
    selected_authority_class: AuthorityClass | None
    semantic_value: Mapping[str, Any] | None
    rejected_candidate_ids: tuple[str, ...]
    conflict_candidate_ids: tuple[str, ...]
    regulatory_overlay_applied: bool

    def __post_init__(self) -> None:
        if not isinstance(self.status, AuthorityResolutionStatus):
            raise AuthorityResolutionError("status must be an AuthorityResolutionStatus")
        if not isinstance(self.as_of_date, date):
            raise AuthorityResolutionError("as_of_date must be a date")
        for field_name in ("concept", "semantic_key"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise AuthorityResolutionError(f"{field_name} must be non-empty text")
            object.__setattr__(self, field_name, value.strip())
        if self.status is AuthorityResolutionStatus.RESOLVED:
            if self.selected_authority_class is None:
                raise AuthorityResolutionError(
                    "resolved result requires selected_authority_class"
                )
            if not isinstance(self.semantic_value, Mapping) or not self.semantic_value:
                raise AuthorityResolutionError(
                    "resolved result requires non-empty semantic_value"
                )
            if not self.selected_candidate_ids:
                raise AuthorityResolutionError(
                    "resolved result requires selected_candidate_ids"
                )
        else:
            if self.semantic_value is not None:
                raise AuthorityResolutionError(
                    "non-resolved result cannot publish semantic_value"
                )


def authority_rank(authority_class: AuthorityClass) -> int:
    if not isinstance(authority_class, AuthorityClass):
        raise AuthorityResolutionError("authority_class must be an AuthorityClass")
    return _AUTHORITY_RANK[authority_class]


def _active_on(candidate: AuthorityCandidate, as_of_date: date) -> bool:
    if candidate.effective_from is not None and as_of_date < candidate.effective_from:
        return False
    if candidate.effective_to is not None and as_of_date > candidate.effective_to:
        return False
    app = candidate.applicability
    if app.effective_from is not None and as_of_date < app.effective_from:
        return False
    if app.effective_to is not None and as_of_date > app.effective_to:
        return False
    return True


def _canonical_value(value: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """Provide deterministic equality for simple governed semantic mappings."""
    return tuple(sorted((str(key), repr(item)) for key, item in value.items()))


def resolve_authority_candidates(
    candidates: Sequence[AuthorityCandidate],
    *,
    concept: str,
    semantic_key: str,
    as_of_date: date,
) -> AuthorityResolution:
    """Resolve candidates by governed authority and fail closed on same-tier conflict.

    Regulatory overlays rank above product documents but remain explicitly identifiable in
    the result. The resolver does not mutate lower-tier contract facts; it selects the effective
    governed interpretation for the requested date.
    """
    if not isinstance(as_of_date, date):
        raise AuthorityResolutionError("as_of_date must be a date")
    if not isinstance(concept, str) or not concept.strip():
        raise AuthorityResolutionError("concept must be non-empty text")
    if not isinstance(semantic_key, str) or not semantic_key.strip():
        raise AuthorityResolutionError("semantic_key must be non-empty text")
    concept = concept.strip()
    semantic_key = semantic_key.strip()

    matching: list[AuthorityCandidate] = []
    rejected: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, AuthorityCandidate):
            raise AuthorityResolutionError("all candidates must be AuthorityCandidate values")
        if candidate.concept != concept or candidate.semantic_key != semantic_key:
            rejected.append(candidate.candidate_id)
            continue
        if not _active_on(candidate, as_of_date):
            rejected.append(candidate.candidate_id)
            continue
        matching.append(candidate)

    if not matching:
        return AuthorityResolution(
            status=AuthorityResolutionStatus.NO_APPLICABLE_CANDIDATE,
            concept=concept,
            semantic_key=semantic_key,
            as_of_date=as_of_date,
            selected_candidate_ids=(),
            selected_authority_class=None,
            semantic_value=None,
            rejected_candidate_ids=tuple(sorted(rejected)),
            conflict_candidate_ids=(),
            regulatory_overlay_applied=False,
        )

    top_rank = max(authority_rank(candidate.authority_class) for candidate in matching)
    top = [
        candidate
        for candidate in matching
        if authority_rank(candidate.authority_class) == top_rank
    ]
    lower = [candidate for candidate in matching if candidate not in top]
    rejected.extend(candidate.candidate_id for candidate in lower)

    values: dict[tuple[tuple[str, str], ...], list[AuthorityCandidate]] = {}
    for candidate in top:
        values.setdefault(_canonical_value(candidate.semantic_value), []).append(candidate)

    if len(values) > 1:
        conflict_ids = tuple(sorted(candidate.candidate_id for candidate in top))
        return AuthorityResolution(
            status=AuthorityResolutionStatus.CONFLICTED,
            concept=concept,
            semantic_key=semantic_key,
            as_of_date=as_of_date,
            selected_candidate_ids=(),
            selected_authority_class=top[0].authority_class,
            semantic_value=None,
            rejected_candidate_ids=tuple(sorted(rejected)),
            conflict_candidate_ids=conflict_ids,
            regulatory_overlay_applied=(
                top[0].authority_class is AuthorityClass.REGULATORY_OVERLAY
            ),
        )

    selected_ids = tuple(sorted(candidate.candidate_id for candidate in top))
    value = top[0].semantic_value
    authority_class = top[0].authority_class
    return AuthorityResolution(
        status=AuthorityResolutionStatus.RESOLVED,
        concept=concept,
        semantic_key=semantic_key,
        as_of_date=as_of_date,
        selected_candidate_ids=selected_ids,
        selected_authority_class=authority_class,
        semantic_value=value,
        rejected_candidate_ids=tuple(sorted(rejected)),
        conflict_candidate_ids=(),
        regulatory_overlay_applied=(authority_class is AuthorityClass.REGULATORY_OVERLAY),
    )


def blocker_for_authority_resolution(
    resolution: AuthorityResolution,
    *,
    applicability: ApplicabilityKey,
) -> PublicationBlocker | None:
    """Convert unresolved authority outcomes into typed publication blockers."""
    if not isinstance(resolution, AuthorityResolution):
        raise AuthorityResolutionError("resolution must be an AuthorityResolution")
    if not isinstance(applicability, ApplicabilityKey):
        raise AuthorityResolutionError("applicability must be an ApplicabilityKey")
    if resolution.status is AuthorityResolutionStatus.RESOLVED:
        return None
    if resolution.status is AuthorityResolutionStatus.CONFLICTED:
        code = (
            PublicationBlockerCode.REGULATORY_CONFLICT
            if resolution.selected_authority_class is AuthorityClass.REGULATORY_OVERLAY
            else PublicationBlockerCode.AUTHORITY_CONFLICT
        )
        ids = resolution.conflict_candidate_ids
        reason = (
            "conflicting equal-authority candidates prevent deterministic publication"
        )
    else:
        code = PublicationBlockerCode.REVIEW_REQUIRED
        ids = ()
        reason = "no applicable governed authority candidate exists for the requested date"
    return PublicationBlocker(
        blocker_id=(
            f"authority_{resolution.concept}_{resolution.semantic_key}_"
            f"{resolution.as_of_date.isoformat()}"
        ),
        code=code,
        concept=resolution.concept,
        applicability=applicability,
        reason=reason,
        normative_unit_ids=ids,
    )


__all__ = [
    "AuthorityCandidate",
    "AuthorityClass",
    "AuthorityResolution",
    "AuthorityResolutionError",
    "AuthorityResolutionStatus",
    "authority_rank",
    "blocker_for_authority_resolution",
    "resolve_authority_candidates",
]
