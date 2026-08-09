"""Generic governed waiting-period publication and coverage projection for MO-028B.G10.

Product-specific values arrive only through governed migration data.  This module composes
G8/G9 migration output, G2 authority resolution and G7 publication eligibility into a certified
publication record, then projects that record into the existing Coverage Registry contract.
It must never branch on insurer/product identity.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Mapping

from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageRecord,
    ConceptCoverageStatus,
    ProductCoverageRecord,
)
from insurance_intelligence.generic_knowledge.authority_resolution import (
    AuthorityCandidate,
    AuthorityClass,
    AuthorityResolution,
    resolve_authority_candidates,
)
from insurance_intelligence.generic_knowledge.contracts import (
    EvidenceReference,
    GenericKnowledgeContractError,
    SemanticFact,
)
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    GovernedReviewStatus,
    PublicationDependencyBinding,
    PublicationEligibilityDecision,
    PublicationEligibilityInput,
    SourceFreshnessStatus,
    evaluate_publication_eligibility,
)
from insurance_intelligence.generic_knowledge.waiting_period_migration import (
    WaitingPeriodMigrationResult,
)


class WaitingPeriodPublicationError(GenericKnowledgeContractError):
    """Raised when generic waiting-period publication inputs violate governance."""


@dataclass(frozen=True)
class GovernedWaitingPeriodPublication:
    publication_id: str
    applicability_product_reference: str
    semantic_facts: tuple[SemanticFact, ...]
    evidence_reference_ids: tuple[str, ...]
    dependency_binding: PublicationDependencyBinding
    eligibility: PublicationEligibilityDecision

    @property
    def published(self) -> bool:
        return self.eligibility.publishable


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodPublicationError(f"{field_name} must be non-empty text")
    return value.strip()


def _authority_resolution(
    migration: WaitingPeriodMigrationResult,
    *,
    authority_class: AuthorityClass,
    as_of_date: date,
) -> AuthorityResolution:
    evidence = EvidenceReference(
        evidence_id=f"authority:{migration.source_document_id}:{migration.source_document_version}",
        source_document_id=migration.source_document_id,
        source_document_version=migration.source_document_version,
        source_hash_sha256=migration.source_hash_sha256,
        locator="governed_migration_source",
        authority_class=authority_class.value,
    )
    candidate = AuthorityCandidate(
        candidate_id=f"authority_candidate:{migration.source_document_id}",
        concept="waiting_periods",
        semantic_key="governed_base_waiting_period_publication",
        semantic_value={"source_hash_sha256": migration.source_hash_sha256},
        applicability=migration.applicability,
        evidence=evidence,
        authority_class=authority_class,
    )
    return resolve_authority_candidates(
        (candidate,),
        concept="waiting_periods",
        semantic_key="governed_base_waiting_period_publication",
        as_of_date=as_of_date,
    )


def publish_waiting_period_migration(
    migration: WaitingPeriodMigrationResult,
    *,
    publication_id: str,
    authority_class: AuthorityClass,
    as_of_date: date,
    review_status: GovernedReviewStatus,
    source_freshness: SourceFreshnessStatus,
    regulatory_overlay_version: str | None = None,
) -> GovernedWaitingPeriodPublication:
    """Create a governed publication only when generic publication gates pass."""
    if not isinstance(migration, WaitingPeriodMigrationResult):
        raise WaitingPeriodPublicationError("migration must be a WaitingPeriodMigrationResult")
    publication_id = _text(publication_id, "publication_id")
    if not isinstance(authority_class, AuthorityClass):
        raise WaitingPeriodPublicationError("authority_class must be an AuthorityClass")
    if not isinstance(as_of_date, date):
        raise WaitingPeriodPublicationError("as_of_date must be a date")

    authority = _authority_resolution(
        migration,
        authority_class=authority_class,
        as_of_date=as_of_date,
    )
    binding = PublicationDependencyBinding(
        ontology_version=migration.ontology_version,
        source_document_id=migration.source_document_id,
        source_document_version=migration.source_document_version,
        source_hash_sha256=migration.source_hash_sha256,
        review_decision_version=migration.review_decision_version,
        regulatory_overlay_version=regulatory_overlay_version,
    )
    eligibility = evaluate_publication_eligibility(
        PublicationEligibilityInput(
            concept="waiting_periods",
            applicability=migration.applicability,
            authority_resolution=authority,
            inventory_accounting=migration.accounting,
            review_status=review_status,
            source_freshness=source_freshness,
            dependency_binding=binding,
        )
    )

    evidence_ids = tuple(
        dict.fromkeys(
            evidence_id
            for fact in migration.mapping.semantic_facts
            for evidence_id in fact.evidence_ids
        )
    )
    return GovernedWaitingPeriodPublication(
        publication_id=publication_id,
        applicability_product_reference=migration.applicability.product_reference,
        semantic_facts=migration.mapping.semantic_facts,
        evidence_reference_ids=evidence_ids,
        dependency_binding=binding,
        eligibility=eligibility,
    )


def project_waiting_period_publication_to_coverage(
    base_product: ProductCoverageRecord,
    publication: GovernedWaitingPeriodPublication,
    *,
    comparison_ready: bool = True,
    decision_support_ready: bool = False,
    limitations: tuple[str, ...] = (),
) -> ProductCoverageRecord:
    """Promote only the waiting-period concept for one exact product applicability."""
    if not isinstance(base_product, ProductCoverageRecord):
        raise WaitingPeriodPublicationError("base_product must be a ProductCoverageRecord")
    if not isinstance(publication, GovernedWaitingPeriodPublication):
        raise WaitingPeriodPublicationError(
            "publication must be a GovernedWaitingPeriodPublication"
        )
    if base_product.product_reference != publication.applicability_product_reference:
        raise WaitingPeriodPublicationError(
            "publication product reference must match coverage product reference"
        )
    if not publication.published:
        raise WaitingPeriodPublicationError(
            "blocked publication cannot promote Coverage Registry state"
        )
    if decision_support_ready and not comparison_ready:
        raise WaitingPeriodPublicationError(
            "decision-support readiness requires comparison readiness"
        )

    coverage_limitations = limitations or (
        "A governed waiting-period assessment policy has not yet been certified for decision-support alignment.",
        "Optional waiting-period modifications and benefit-scoped waivers require separately governed relationship/optional-cover publication before downstream use.",
    )
    promoted: list[ConceptCoverageRecord] = []
    found = False
    for concept in base_product.concepts:
        if concept.concept_id != "waiting_periods":
            promoted.append(concept)
            continue
        found = True
        promoted.append(
            ConceptCoverageRecord(
                concept_id="waiting_periods",
                status=ConceptCoverageStatus.CERTIFIED,
                evidence_reference_ids=publication.evidence_reference_ids,
                comparison_ready=comparison_ready,
                decision_support_ready=decision_support_ready,
                limitations=coverage_limitations,
            )
        )
    if not found:
        promoted.append(
            ConceptCoverageRecord(
                concept_id="waiting_periods",
                status=ConceptCoverageStatus.CERTIFIED,
                evidence_reference_ids=publication.evidence_reference_ids,
                comparison_ready=comparison_ready,
                decision_support_ready=decision_support_ready,
                limitations=coverage_limitations,
            )
        )
    return replace(base_product, concepts=tuple(promoted))


__all__ = [
    "GovernedWaitingPeriodPublication",
    "WaitingPeriodPublicationError",
    "project_waiting_period_publication_to_coverage",
    "publish_waiting_period_migration",
]
