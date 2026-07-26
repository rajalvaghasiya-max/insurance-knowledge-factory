from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from insurance_intelligence.contracts.terminology import (
    AliasCandidate,
    CanonicalConceptFamily,
    EvidenceSpan,
    InsurerMarketingTerm,
    ProductTermImplementation,
    ResolverConfidence,
    ResolverConfidenceBand,
    TerminologyContractError,
    TerminologyPublicationStatus,
    TerminologyRelationship,
    TerminologyRelationshipDecision,
    TerminologyResolutionResult,
    TerminologyReviewStatus,
    UnresolvedTerminologyRecord,
)


def _evidence() -> tuple[EvidenceSpan, ...]:
    return (
        EvidenceSpan(
            source_id="source-1",
            document_id="document-1",
            locator="page 12",
            quoted_text="The benefit restores the sum insured.",
            evidence_id="evidence-1",
        ),
    )


def _term() -> InsurerMarketingTerm:
    return InsurerMarketingTerm(
        term_id="term-1",
        display_name="Restore Benefit",
        insurer_id="insurer-1",
        product_id="product-1",
        product_variant_id="variant-1",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        evidence_spans=_evidence(),
        review_status=TerminologyReviewStatus.HUMAN_APPROVED,
        publication_status=TerminologyPublicationStatus.ELIGIBLE,
    )


def _concept() -> CanonicalConceptFamily:
    return CanonicalConceptFamily(
        concept_family_id="concept-restoration",
        canonical_name="Sum Insured Restoration",
        definition="Reinstatement of eligible coverage after utilisation.",
        domain="health",
        concept_subtype="restoration",
    )


def _implementation() -> ProductTermImplementation:
    return ProductTermImplementation(
        implementation_id="implementation-1",
        term_id="term-1",
        concept_family_id="concept-restoration",
        behaviour_signature_id=None,
        conditions=("Available after eligible utilisation.",),
        limitations=("Subject to product wording.",),
        evidence_spans=_evidence(),
    )


def _confidence() -> ResolverConfidence:
    return ResolverConfidence(
        score=0.92,
        band=ResolverConfidenceBand.VERY_HIGH,
        rationale=("Definition and behaviour align.",),
    )


def test_evidence_span_requires_source_identity() -> None:
    with pytest.raises(TerminologyContractError, match="source_id"):
        EvidenceSpan(
            source_id="",
            document_id="document-1",
            locator="page 1",
            quoted_text="Text",
        )


def test_marketing_term_is_product_scoped() -> None:
    term = _term()
    assert term.insurer_id == "insurer-1"
    assert term.product_id == "product-1"
    assert term.product_variant_id == "variant-1"


def test_marketing_term_requires_evidence() -> None:
    with pytest.raises(TerminologyContractError, match="evidence"):
        InsurerMarketingTerm(
            term_id="term-1",
            display_name="Restore",
            insurer_id="insurer-1",
            product_id="product-1",
            product_variant_id=None,
            effective_from=None,
            effective_to=None,
            evidence_spans=(),
            review_status=TerminologyReviewStatus.DISCOVERED,
            publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
        )


def test_marketing_term_rejects_invalid_effective_dates() -> None:
    with pytest.raises(TerminologyContractError, match="effective_to"):
        InsurerMarketingTerm(
            term_id="term-1",
            display_name="Restore",
            insurer_id="insurer-1",
            product_id="product-1",
            product_variant_id=None,
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 1, 1),
            evidence_spans=_evidence(),
            review_status=TerminologyReviewStatus.DISCOVERED,
            publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
        )


def test_authoritative_term_requires_published_review() -> None:
    with pytest.raises(TerminologyContractError, match="PUBLISHED"):
        InsurerMarketingTerm(
            term_id="term-1",
            display_name="Restore",
            insurer_id="insurer-1",
            product_id="product-1",
            product_variant_id=None,
            effective_from=None,
            effective_to=None,
            evidence_spans=_evidence(),
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.AUTHORITATIVE,
        )


def test_concept_family_rejects_self_parent() -> None:
    with pytest.raises(TerminologyContractError, match="own parent"):
        CanonicalConceptFamily(
            concept_family_id="concept-1",
            canonical_name="Concept",
            definition="Definition",
            domain="health",
            parent_concept_family_id="concept-1",
        )


def test_implementation_preserves_conditions_and_limitations() -> None:
    implementation = _implementation()
    assert implementation.conditions == (
        "Available after eligible utilisation.",
    )
    assert implementation.limitations == ("Subject to product wording.",)


def test_text_collections_reject_duplicates() -> None:
    with pytest.raises(TerminologyContractError, match="duplicates"):
        ProductTermImplementation(
            implementation_id="implementation-1",
            term_id="term-1",
            concept_family_id="concept-1",
            behaviour_signature_id=None,
            conditions=("Condition", "Condition"),
            limitations=(),
            evidence_spans=_evidence(),
        )


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_confidence_score_must_be_bounded(score: float) -> None:
    with pytest.raises(TerminologyContractError, match="between 0 and 1"):
        ResolverConfidence(
            score=score,
            band=ResolverConfidenceBand.MEDIUM,
            rationale=("Reason",),
        )


def test_confidence_requires_rationale() -> None:
    with pytest.raises(TerminologyContractError, match="must not be empty"):
        ResolverConfidence(
            score=0.5,
            band=ResolverConfidenceBand.MEDIUM,
            rationale=(),
        )


def test_alias_candidate_cannot_be_unresolved() -> None:
    with pytest.raises(TerminologyContractError, match="concrete"):
        AliasCandidate(
            candidate_id="candidate-1",
            term_id="term-1",
            candidate_concept_family_id="concept-1",
            relationship=TerminologyRelationship.UNRESOLVED,
            confidence=_confidence(),
            evidence_spans=_evidence(),
            review_status=TerminologyReviewStatus.CANDIDATE,
        )


def test_relationship_decision_requires_two_implementations() -> None:
    with pytest.raises(TerminologyContractError, match="different"):
        TerminologyRelationshipDecision(
            decision_id="decision-1",
            left_implementation_id="implementation-1",
            right_implementation_id="implementation-1",
            relationship=TerminologyRelationship.EXACT_EQUIVALENT,
            rationale=("Same behaviour.",),
            evidence_spans=_evidence(),
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.ELIGIBLE,
        )


def test_unresolved_record_cannot_be_published() -> None:
    with pytest.raises(TerminologyContractError, match="cannot be PUBLISHED"):
        UnresolvedTerminologyRecord(
            unresolved_id="unresolved-1",
            term_id="term-1",
            reason_codes=("INSUFFICIENT_BEHAVIOUR_EVIDENCE",),
            missing_information=("Current policy wording",),
            evidence_spans=_evidence(),
            review_status=TerminologyReviewStatus.PUBLISHED,
        )


def test_unresolved_resolution_fails_closed() -> None:
    unresolved = UnresolvedTerminologyRecord(
        unresolved_id="unresolved-1",
        term_id="term-1",
        reason_codes=("INSUFFICIENT_BEHAVIOUR_EVIDENCE",),
        missing_information=("Current policy wording",),
        evidence_spans=_evidence(),
    )
    result = TerminologyResolutionResult(
        resolution_id="resolution-1",
        term=_term(),
        selected_concept=None,
        implementation=None,
        relationship=TerminologyRelationship.UNRESOLVED,
        confidence=None,
        alias_candidates=(),
        unresolved=unresolved,
        review_status=TerminologyReviewStatus.REVIEW_REQUIRED,
        publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
    )
    assert result.relationship is TerminologyRelationship.UNRESOLVED
    assert result.selected_concept is None


def test_unresolved_resolution_cannot_publish_mapping() -> None:
    unresolved = UnresolvedTerminologyRecord(
        unresolved_id="unresolved-1",
        term_id="term-1",
        reason_codes=("INSUFFICIENT_BEHAVIOUR_EVIDENCE",),
        missing_information=("Current policy wording",),
        evidence_spans=_evidence(),
    )
    with pytest.raises(TerminologyContractError, match="cannot publish"):
        TerminologyResolutionResult(
            resolution_id="resolution-1",
            term=_term(),
            selected_concept=_concept(),
            implementation=_implementation(),
            relationship=TerminologyRelationship.UNRESOLVED,
            confidence=_confidence(),
            alias_candidates=(),
            unresolved=unresolved,
            review_status=TerminologyReviewStatus.REVIEW_REQUIRED,
            publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
        )


def test_resolved_result_requires_selected_concept() -> None:
    with pytest.raises(TerminologyContractError, match="selected concept"):
        TerminologyResolutionResult(
            resolution_id="resolution-1",
            term=_term(),
            selected_concept=None,
            implementation=_implementation(),
            relationship=TerminologyRelationship.FUNCTIONALLY_SIMILAR,
            confidence=_confidence(),
            alias_candidates=(),
            unresolved=None,
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.ELIGIBLE,
        )


def test_resolved_result_requires_matching_term_identity() -> None:
    implementation = ProductTermImplementation(
        implementation_id="implementation-1",
        term_id="term-other",
        concept_family_id="concept-restoration",
        behaviour_signature_id=None,
        conditions=(),
        limitations=(),
        evidence_spans=_evidence(),
    )
    with pytest.raises(TerminologyContractError, match="term_id"):
        TerminologyResolutionResult(
            resolution_id="resolution-1",
            term=_term(),
            selected_concept=_concept(),
            implementation=implementation,
            relationship=TerminologyRelationship.FUNCTIONALLY_SIMILAR,
            confidence=_confidence(),
            alias_candidates=(),
            unresolved=None,
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.ELIGIBLE,
        )


def test_resolved_result_requires_matching_concept_identity() -> None:
    concept = CanonicalConceptFamily(
        concept_family_id="concept-other",
        canonical_name="Other",
        definition="Other concept",
        domain="health",
    )
    with pytest.raises(TerminologyContractError, match="concept_family_id"):
        TerminologyResolutionResult(
            resolution_id="resolution-1",
            term=_term(),
            selected_concept=concept,
            implementation=_implementation(),
            relationship=TerminologyRelationship.FUNCTIONALLY_SIMILAR,
            confidence=_confidence(),
            alias_candidates=(),
            unresolved=None,
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.ELIGIBLE,
        )


def test_resolved_result_is_immutable() -> None:
    result = TerminologyResolutionResult(
        resolution_id="resolution-1",
        term=_term(),
        selected_concept=_concept(),
        implementation=_implementation(),
        relationship=TerminologyRelationship.FUNCTIONALLY_SIMILAR,
        confidence=_confidence(),
        alias_candidates=(),
        unresolved=None,
        review_status=TerminologyReviewStatus.HUMAN_APPROVED,
        publication_status=TerminologyPublicationStatus.ELIGIBLE,
    )
    with pytest.raises(FrozenInstanceError):
        result.resolution_id = "changed"  # type: ignore[misc]


def test_authoritative_resolution_requires_published_review() -> None:
    with pytest.raises(TerminologyContractError, match="PUBLISHED"):
        TerminologyResolutionResult(
            resolution_id="resolution-1",
            term=_term(),
            selected_concept=_concept(),
            implementation=_implementation(),
            relationship=TerminologyRelationship.FUNCTIONALLY_SIMILAR,
            confidence=_confidence(),
            alias_candidates=(),
            unresolved=None,
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.AUTHORITATIVE,
        )


def test_all_relationship_types_are_stable() -> None:
    assert {item.value for item in TerminologyRelationship} == {
        "EXACT_EQUIVALENT",
        "FUNCTIONALLY_SIMILAR",
        "SAME_CONCEPT_DIFFERENT_SCOPE",
        "BROADER_THAN",
        "NARROWER_THAN",
        "CONDITIONAL_VARIANT",
        "COMPOSITE_IMPLEMENTATION",
        "MARKETING_ALIAS_ONLY",
        "NOT_EQUIVALENT",
        "UNRESOLVED",
    }
