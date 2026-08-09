"""Generic publication eligibility and dependency binding for MO-028B.G7.

This module composes existing generic governance outcomes into one deterministic
publish-or-block decision. It is product-agnostic: product identity is carried only
inside ApplicabilityKey data and never used for branching.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from insurance_intelligence.generic_knowledge.authority_resolution import (
    AuthorityResolution,
    ResolutionStatus,
    blocker_for_authority_resolution,
)
from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    GenericKnowledgeContractError,
    PublicationBlocker,
    PublicationBlockerCode,
)
from insurance_intelligence.generic_knowledge.normative_inventory import (
    InventoryAccountingResult,
    InventoryReviewStatus,
)


class PublicationEligibilityError(GenericKnowledgeContractError):
    """Raised when publication-eligibility inputs violate generic governance."""


class GovernedReviewStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SourceFreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


class PublicationEligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    BLOCKED = "BLOCKED"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationEligibilityError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class PublicationDependencyBinding:
    ontology_version: str
    source_document_id: str
    source_document_version: str
    source_hash_sha256: str
    review_decision_version: str
    regulatory_overlay_version: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "ontology_version",
            "source_document_id",
            "source_document_version",
            "source_hash_sha256",
            "review_decision_version",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if self.regulatory_overlay_version is not None:
            object.__setattr__(
                self,
                "regulatory_overlay_version",
                _text(self.regulatory_overlay_version, "regulatory_overlay_version"),
            )


@dataclass(frozen=True)
class PublicationEligibilityInput:
    concept: str
    applicability: ApplicabilityKey
    authority_resolution: AuthorityResolution
    inventory_accounting: InventoryAccountingResult
    review_status: GovernedReviewStatus
    source_freshness: SourceFreshnessStatus
    dependency_binding: PublicationDependencyBinding

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept", _text(self.concept, "concept"))
        if not isinstance(self.applicability, ApplicabilityKey):
            raise PublicationEligibilityError("applicability must be an ApplicabilityKey")
        if not isinstance(self.authority_resolution, AuthorityResolution):
            raise PublicationEligibilityError(
                "authority_resolution must be an AuthorityResolution"
            )
        if not isinstance(self.inventory_accounting, InventoryAccountingResult):
            raise PublicationEligibilityError(
                "inventory_accounting must be an InventoryAccountingResult"
            )
        if not isinstance(self.review_status, GovernedReviewStatus):
            raise PublicationEligibilityError("review_status must be a GovernedReviewStatus")
        if not isinstance(self.source_freshness, SourceFreshnessStatus):
            raise PublicationEligibilityError(
                "source_freshness must be a SourceFreshnessStatus"
            )
        if not isinstance(self.dependency_binding, PublicationDependencyBinding):
            raise PublicationEligibilityError(
                "dependency_binding must be a PublicationDependencyBinding"
            )
        if self.authority_resolution.concept != self.concept:
            raise PublicationEligibilityError(
                "authority_resolution concept must match publication concept"
            )
        if self.inventory_accounting.concept != self.concept:
            raise PublicationEligibilityError(
                "inventory_accounting concept must match publication concept"
            )


@dataclass(frozen=True)
class PublicationEligibilityDecision:
    status: PublicationEligibilityStatus
    concept: str
    applicability: ApplicabilityKey
    dependency_binding: PublicationDependencyBinding
    blockers: tuple[PublicationBlocker, ...]

    @property
    def publishable(self) -> bool:
        return self.status is PublicationEligibilityStatus.ELIGIBLE


def _blocker(
    *,
    concept: str,
    applicability: ApplicabilityKey,
    code: PublicationBlockerCode,
    reason: str,
    suffix: str,
) -> PublicationBlocker:
    return PublicationBlocker(
        blocker_id=f"publication_{concept}_{suffix}",
        code=code,
        concept=concept,
        applicability=applicability,
        reason=reason,
    )


def evaluate_publication_eligibility(
    publication: PublicationEligibilityInput,
) -> PublicationEligibilityDecision:
    """Return a deterministic publication decision for one concept/applicability unit."""
    if not isinstance(publication, PublicationEligibilityInput):
        raise PublicationEligibilityError(
            "publication must be a PublicationEligibilityInput"
        )

    blockers: list[PublicationBlocker] = list(publication.inventory_accounting.blockers)

    authority_blocker = blocker_for_authority_resolution(
        publication.authority_resolution,
        applicability=publication.applicability,
    )
    if authority_blocker is not None:
        blockers.append(authority_blocker)

    if publication.inventory_accounting.telemetry.normative_unit_count <= 0:
        raise PublicationEligibilityError(
            "publication requires a non-empty normative inventory"
        )

    if publication.review_status is not GovernedReviewStatus.APPROVED:
        blockers.append(
            _blocker(
                concept=publication.concept,
                applicability=publication.applicability,
                code=PublicationBlockerCode.REVIEW_REQUIRED,
                reason=(
                    "governed review is not approved"
                    if publication.review_status is GovernedReviewStatus.UNREVIEWED
                    else "governed review rejected publication"
                ),
                suffix="review",
            )
        )

    if publication.source_freshness is not SourceFreshnessStatus.CURRENT:
        blockers.append(
            _blocker(
                concept=publication.concept,
                applicability=publication.applicability,
                code=PublicationBlockerCode.SOURCE_STALE,
                reason=(
                    "source has been superseded"
                    if publication.source_freshness is SourceFreshnessStatus.SUPERSEDED
                    else "source freshness is unknown"
                ),
                suffix="source_freshness",
            )
        )

    # Inventory review is distinct from semantic/governed approval. An unreviewed
    # high-recall inventory means the source-coverage accounting itself is not certified.
    # The current G3 result retains inventory method/version but not review state, so this
    # gate relies on semantic governed review plus zero material residue until review state
    # is carried into the result in a later backward-compatible extension.

    # Deterministic blocker de-duplication while preserving independent reasons.
    deduped: dict[tuple[str, str, str], PublicationBlocker] = {}
    for blocker in blockers:
        key = (blocker.code.value, blocker.blocker_id, blocker.reason)
        deduped[key] = blocker
    ordered = tuple(
        sorted(
            deduped.values(),
            key=lambda item: (item.code.value, item.blocker_id, item.reason),
        )
    )

    return PublicationEligibilityDecision(
        status=(
            PublicationEligibilityStatus.BLOCKED
            if ordered
            else PublicationEligibilityStatus.ELIGIBLE
        ),
        concept=publication.concept,
        applicability=publication.applicability,
        dependency_binding=publication.dependency_binding,
        blockers=ordered,
    )


def dependency_binding_matches(
    published: PublicationDependencyBinding,
    current: PublicationDependencyBinding,
) -> bool:
    """Return whether a publication's governed dependencies are still exact/current."""
    if not isinstance(published, PublicationDependencyBinding) or not isinstance(
        current, PublicationDependencyBinding
    ):
        raise PublicationEligibilityError(
            "published and current must be PublicationDependencyBinding values"
        )
    return published == current


__all__ = [
    "GovernedReviewStatus",
    "PublicationDependencyBinding",
    "PublicationEligibilityDecision",
    "PublicationEligibilityError",
    "PublicationEligibilityInput",
    "PublicationEligibilityStatus",
    "SourceFreshnessStatus",
    "dependency_binding_matches",
    "evaluate_publication_eligibility",
]
