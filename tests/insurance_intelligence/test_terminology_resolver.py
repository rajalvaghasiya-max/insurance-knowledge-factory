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
    TerminologyPublicationStatus,
    TerminologyRelationship,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.resolver import (
    TerminologyResolver,
    normalise_terminology_text,
)


def evidence(label: str = "term") -> EvidenceSpan:
    return EvidenceSpan(
        source_id=f"source:{label}",
        document_id=f"document:{label}",
        locator="page:1",
        quoted_text=f"Evidence for {label}",
    )


def term(
    *,
    term_id: str = "term:benefit-a",
    display_name: str = "Benefit A",
    insurer_id: str = "insurer:one",
    product_id: str = "product:one",
    variant_id: str | None = None,
    effective_from: date | None = date(2025, 1, 1),
    effective_to: date | None = None,
    review_status: TerminologyReviewStatus = TerminologyReviewStatus.PUBLISHED,
    publication_status: TerminologyPublicationStatus = TerminologyPublicationStatus.AUTHORITATIVE,
) -> InsurerMarketingTerm:
    return InsurerMarketingTerm(
        term_id=term_id,
        display_name=display_name,
        insurer_id=insurer_id,
        product_id=product_id,
        product_variant_id=variant_id,
        effective_from=effective_from,
        effective_to=effective_to,
        evidence_spans=(evidence(term_id),),
        review_status=review_status,
        publication_status=publication_status,
    )


def implementation(
    *,
    implementation_id: str = "implementation:one",
    term_id: str = "term:benefit-a",
    concept_id: str = "concept:benefit",
    effective_from: date | None = date(2025, 1, 1),
    effective_to: date | None = None,
) -> ProductTermImplementation:
    return ProductTermImplementation(
        implementation_id=implementation_id,
        term_id=term_id,
        concept_family_id=concept_id,
        behaviour_signature_id=None,
        conditions=(),
        limitations=(),
        evidence_spans=(evidence(implementation_id),),
        effective_from=effective_from,
        effective_to=effective_to,
    )


def concept(concept_id: str = "concept:benefit") -> CanonicalConceptFamily:
    return CanonicalConceptFamily(
        concept_family_id=concept_id,
        canonical_name="Canonical Benefit",
        definition="A governed benefit concept.",
        domain="health",
    )


def resolver(
    *,
    terms=(),
    implementations=(),
    concepts=(),
    alias_candidates=(),
) -> TerminologyResolver:
    return TerminologyResolver(
        marketing_terms=tuple(terms),
        implementations=tuple(implementations),
        concepts=tuple(concepts),
        alias_candidates=tuple(alias_candidates),
    )


def test_normalisation_is_exact_but_case_and_whitespace_insensitive() -> None:
    assert normalise_terminology_text("  BENEFIT\tA  ") == "benefit a"
    assert normalise_terminology_text("Ａ") == "a"


def test_normalisation_rejects_non_text() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        normalise_terminology_text(123)  # type: ignore[arg-type]


def test_resolves_unique_governed_mapping() -> None:
    query = term(display_name="  benefit   A ")
    governed = term()
    result = resolver(
        terms=(governed,),
        implementations=(implementation(),),
        concepts=(concept(),),
    ).resolve(query, as_of=date(2026, 1, 1))

    assert result.relationship is TerminologyRelationship.EXACT_EQUIVALENT
    assert result.term is governed
    assert result.selected_concept == concept()
    assert result.implementation == implementation()
    assert result.confidence is not None
    assert result.confidence.score == 1.0
    assert result.publication_status is TerminologyPublicationStatus.AUTHORITATIVE


def test_resolution_ids_are_stable() -> None:
    governed = term()
    service = resolver(
        terms=(governed,),
        implementations=(implementation(),),
        concepts=(concept(),),
    )
    first = service.resolve(governed, as_of=date(2026, 1, 1))
    second = service.resolve(governed, as_of=date(2026, 1, 1))
    assert first.resolution_id == second.resolution_id


def test_no_match_fails_closed() -> None:
    query = term()
    result = resolver().resolve(query, as_of=date(2026, 1, 1))
    assert result.relationship is TerminologyRelationship.UNRESOLVED
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("NO_MATCHING_GOVERNED_TERM",)
    assert result.publication_status is TerminologyPublicationStatus.NOT_PUBLISHED


def test_scope_mismatch_is_not_a_match() -> None:
    query = term(product_id="product:requested")
    other = term(product_id="product:other")
    result = resolver(terms=(other,)).resolve(query, as_of=date(2026, 1, 1))
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("NO_MATCHING_GOVERNED_TERM",)


def test_variant_mismatch_is_not_a_match() -> None:
    query = term(variant_id="variant:a")
    other = term(variant_id="variant:b")
    result = resolver(terms=(other,)).resolve(query, as_of=date(2026, 1, 1))
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("NO_MATCHING_GOVERNED_TERM",)


def test_inactive_term_is_not_a_match() -> None:
    query = term()
    expired = term(effective_to=date(2025, 12, 31))
    result = resolver(terms=(expired,)).resolve(query, as_of=date(2026, 1, 1))
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("NO_MATCHING_GOVERNED_TERM",)


def test_multiple_active_terms_fail_closed() -> None:
    query = term()
    result = resolver(
        terms=(term(term_id="term:one"), term(term_id="term:two")),
    ).resolve(query, as_of=date(2026, 1, 1))
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("MULTIPLE_ACTIVE_TERM_RECORDS",)
    assert len(result.unresolved.evidence_spans) == 2


@pytest.mark.parametrize(
    ("review_status", "publication_status"),
    [
        (
            TerminologyReviewStatus.AUTO_VALIDATED,
            TerminologyPublicationStatus.ELIGIBLE,
        ),
        (
            TerminologyReviewStatus.PUBLISHED,
            TerminologyPublicationStatus.NOT_PUBLISHED,
        ),
    ],
)
def test_insufficient_governance_fails_closed(
    review_status: TerminologyReviewStatus,
    publication_status: TerminologyPublicationStatus,
) -> None:
    governed = term(
        review_status=review_status,
        publication_status=publication_status,
    )
    result = resolver(terms=(governed,)).resolve(
        governed, as_of=date(2026, 1, 1)
    )
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("TERM_NOT_GOVERNED_FOR_RESOLUTION",)


def test_missing_implementation_fails_closed() -> None:
    governed = term()
    result = resolver(terms=(governed,)).resolve(
        governed, as_of=date(2026, 1, 1)
    )
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("MISSING_PRODUCT_IMPLEMENTATION",)


def test_multiple_active_implementations_fail_closed() -> None:
    governed = term()
    result = resolver(
        terms=(governed,),
        implementations=(
            implementation(implementation_id="implementation:one"),
            implementation(implementation_id="implementation:two"),
        ),
    ).resolve(governed, as_of=date(2026, 1, 1))
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("MULTIPLE_ACTIVE_IMPLEMENTATIONS",)


def test_inactive_implementation_is_ignored() -> None:
    governed = term()
    result = resolver(
        terms=(governed,),
        implementations=(
            implementation(
                implementation_id="implementation:expired",
                effective_to=date(2025, 12, 31),
            ),
            implementation(implementation_id="implementation:active"),
        ),
        concepts=(concept(),),
    ).resolve(governed, as_of=date(2026, 1, 1))
    assert result.implementation is not None
    assert result.implementation.implementation_id == "implementation:active"


def test_missing_concept_fails_closed() -> None:
    governed = term()
    result = resolver(
        terms=(governed,),
        implementations=(implementation(),),
    ).resolve(governed, as_of=date(2026, 1, 1))
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("MISSING_CANONICAL_CONCEPT",)


def test_duplicate_concept_identifier_fails_closed() -> None:
    governed = term()
    result = resolver(
        terms=(governed,),
        implementations=(implementation(),),
        concepts=(concept(), concept()),
    ).resolve(governed, as_of=date(2026, 1, 1))
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("DUPLICATE_CANONICAL_CONCEPT",)


def test_alias_candidates_are_carried_in_stable_order() -> None:
    governed = term()
    confidence = ResolverConfidence(
        score=0.8,
        band=ResolverConfidenceBand.HIGH,
        rationale=("Governed candidate",),
    )
    candidates = (
        AliasCandidate(
            candidate_id="candidate:z",
            term_id=governed.term_id,
            candidate_concept_family_id="concept:other",
            relationship=TerminologyRelationship.FUNCTIONALLY_SIMILAR,
            confidence=confidence,
            evidence_spans=(evidence("candidate:z"),),
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
        ),
        AliasCandidate(
            candidate_id="candidate:a",
            term_id=governed.term_id,
            candidate_concept_family_id="concept:another",
            relationship=TerminologyRelationship.SAME_CONCEPT_DIFFERENT_SCOPE,
            confidence=confidence,
            evidence_spans=(evidence("candidate:a"),),
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
        ),
    )
    result = resolver(
        terms=(governed,),
        implementations=(implementation(),),
        concepts=(concept(),),
        alias_candidates=candidates,
    ).resolve(governed, as_of=date(2026, 1, 1))
    assert [item.candidate_id for item in result.alias_candidates] == [
        "candidate:a",
        "candidate:z",
    ]


def test_unrelated_alias_candidates_are_not_carried() -> None:
    governed = term()
    candidate = AliasCandidate(
        candidate_id="candidate:other",
        term_id="term:other",
        candidate_concept_family_id="concept:other",
        relationship=TerminologyRelationship.FUNCTIONALLY_SIMILAR,
        confidence=ResolverConfidence(
            score=0.7,
            band=ResolverConfidenceBand.HIGH,
            rationale=("Governed candidate",),
        ),
        evidence_spans=(evidence("candidate:other"),),
        review_status=TerminologyReviewStatus.HUMAN_APPROVED,
    )
    result = resolver(
        terms=(governed,),
        implementations=(implementation(),),
        concepts=(concept(),),
        alias_candidates=(candidate,),
    ).resolve(governed, as_of=date(2026, 1, 1))
    assert result.alias_candidates == ()
