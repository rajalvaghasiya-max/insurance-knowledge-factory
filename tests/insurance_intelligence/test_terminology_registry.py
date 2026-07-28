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
    TerminologyPublicationStatus,
    TerminologyRelationship,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.registry import (
    TerminologyRegistryError,
    TerminologyRegistrySnapshot,
)


def evidence(label: str) -> EvidenceSpan:
    return EvidenceSpan(
        source_id=f"source:{label}",
        document_id=f"document:{label}",
        locator="page:1",
        quoted_text=f"Evidence for {label}",
    )


def term(term_id: str = "term:copay") -> InsurerMarketingTerm:
    return InsurerMarketingTerm(
        term_id=term_id,
        display_name="Co-payment",
        insurer_id="insurer:one",
        product_id="product:one",
        product_variant_id=None,
        effective_from=date(2025, 1, 1),
        effective_to=None,
        evidence_spans=(evidence(term_id),),
        review_status=TerminologyReviewStatus.PUBLISHED,
        publication_status=TerminologyPublicationStatus.AUTHORITATIVE,
    )


def concept(concept_id: str = "concept:copay") -> CanonicalConceptFamily:
    return CanonicalConceptFamily(
        concept_family_id=concept_id,
        canonical_name="Copayment",
        definition="A governed cost-sharing concept.",
        domain="health",
    )


def implementation(
    implementation_id: str = "implementation:copay",
    *,
    term_id: str = "term:copay",
    concept_id: str = "concept:copay",
) -> ProductTermImplementation:
    return ProductTermImplementation(
        implementation_id=implementation_id,
        term_id=term_id,
        concept_family_id=concept_id,
        behaviour_signature_id=None,
        conditions=("Applies to an admissible claim.",),
        limitations=("Subject to policy wording.",),
        evidence_spans=(evidence(implementation_id),),
        effective_from=date(2025, 1, 1),
        effective_to=None,
    )


def alias_candidate(
    candidate_id: str = "candidate:copay",
    *,
    term_id: str = "term:copay",
    concept_id: str = "concept:copay",
) -> AliasCandidate:
    return AliasCandidate(
        candidate_id=candidate_id,
        term_id=term_id,
        candidate_concept_family_id=concept_id,
        relationship=TerminologyRelationship.MARKETING_ALIAS_ONLY,
        confidence=ResolverConfidence(
            score=1.0,
            band=ResolverConfidenceBand.VERY_HIGH,
            rationale=("Controlled governed alias candidate.",),
        ),
        evidence_spans=(evidence(candidate_id),),
        review_status=TerminologyReviewStatus.HUMAN_APPROVED,
    )


def snapshot() -> TerminologyRegistrySnapshot:
    return TerminologyRegistrySnapshot(
        marketing_terms=(term(),),
        implementations=(implementation(),),
        concepts=(concept(),),
        alias_candidates=(alias_candidate(),),
    )


def test_snapshot_is_immutable() -> None:
    registry = snapshot()
    with pytest.raises(FrozenInstanceError):
        registry.concepts = ()  # type: ignore[misc]


def test_snapshot_id_is_stable_and_order_independent() -> None:
    first = TerminologyRegistrySnapshot(
        marketing_terms=(term("term:b"), term("term:a")),
        implementations=(
            implementation("implementation:b", term_id="term:b"),
            implementation("implementation:a", term_id="term:a"),
        ),
        concepts=(concept(),),
    )
    second = TerminologyRegistrySnapshot(
        marketing_terms=(term("term:a"), term("term:b")),
        implementations=(
            implementation("implementation:a", term_id="term:a"),
            implementation("implementation:b", term_id="term:b"),
        ),
        concepts=(concept(),),
    )
    assert first.snapshot_id == second.snapshot_id


@pytest.mark.parametrize(
    ("field", "kwargs", "expected"),
    [
        (
            "term",
            {"marketing_terms": (term(), term())},
            "duplicate term_id",
        ),
        (
            "implementation",
            {"implementations": (implementation(), implementation())},
            "duplicate implementation_id",
        ),
        (
            "concept",
            {"concepts": (concept(), concept())},
            "duplicate concept_family_id",
        ),
        (
            "candidate",
            {"alias_candidates": (alias_candidate(), alias_candidate())},
            "duplicate candidate_id",
        ),
    ],
)
def test_duplicate_identifiers_fail_closed(
    field: str, kwargs: dict, expected: str
) -> None:
    values = {
        "marketing_terms": (term(),),
        "implementations": (implementation(),),
        "concepts": (concept(),),
        "alias_candidates": (alias_candidate(),),
    }
    values.update(kwargs)
    with pytest.raises(TerminologyRegistryError, match=expected):
        TerminologyRegistrySnapshot(**values)


def test_unknown_implementation_term_fails_closed() -> None:
    with pytest.raises(TerminologyRegistryError, match="unknown term_id"):
        TerminologyRegistrySnapshot(
            marketing_terms=(term(),),
            implementations=(implementation(term_id="term:missing"),),
            concepts=(concept(),),
        )


def test_unknown_implementation_concept_fails_closed() -> None:
    with pytest.raises(TerminologyRegistryError, match="unknown concept_family_id"):
        TerminologyRegistrySnapshot(
            marketing_terms=(term(),),
            implementations=(implementation(concept_id="concept:missing"),),
            concepts=(concept(),),
        )


def test_unknown_alias_term_fails_closed() -> None:
    with pytest.raises(TerminologyRegistryError, match="unknown term_id"):
        TerminologyRegistrySnapshot(
            marketing_terms=(term(),),
            implementations=(implementation(),),
            concepts=(concept(),),
            alias_candidates=(alias_candidate(term_id="term:missing"),),
        )


def test_unknown_alias_concept_fails_closed() -> None:
    with pytest.raises(TerminologyRegistryError, match="unknown concept_family_id"):
        TerminologyRegistrySnapshot(
            marketing_terms=(term(),),
            implementations=(implementation(),),
            concepts=(concept(),),
            alias_candidates=(alias_candidate(concept_id="concept:missing"),),
        )


def test_snapshot_builds_existing_deterministic_resolver() -> None:
    registry = snapshot()
    result = registry.build_resolver().resolve(term(), as_of=date(2026, 1, 1))
    assert result.relationship is TerminologyRelationship.EXACT_EQUIVALENT
    assert result.selected_concept == concept()
    assert result.implementation == implementation()


def test_registry_does_not_merge_legacy_canonical_vocabulary() -> None:
    registry = snapshot()
    assert {item.concept_family_id for item in registry.concepts} == {"concept:copay"}
