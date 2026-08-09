from dataclasses import replace
from datetime import date

import pytest

from insurance_intelligence.contracts.terminology import (
    EvidenceSpan,
    TerminologyPublicationStatus,
    TerminologyRelationship,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.alias_resolver import (
    ExactAliasTerminologyResolver,
    GovernedTerminologyAlias,
    TerminologyAliasError,
)
from insurance_intelligence.terminology.star_comprehensive_aliases import (
    STAR_COMPREHENSIVE_COPAYMENT_ALIASES,
    build_star_comprehensive_alias_resolver,
)
from insurance_intelligence.terminology.star_comprehensive_catalogue import (
    STAR_COMPREHENSIVE_COPAYMENT_TERM,
    build_star_comprehensive_copayment_snapshot,
)

AS_OF = date(2026, 7, 29)


def query(display_name: str):
    return replace(
        STAR_COMPREHENSIVE_COPAYMENT_TERM,
        term_id=f"query:{display_name}",
        display_name=display_name,
        review_status=TerminologyReviewStatus.DISCOVERED,
        publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
    )


@pytest.mark.parametrize("alias_text", ["Co pay", "Co payment", "Copay"])
def test_controlled_star_aliases_resolve(alias_text: str) -> None:
    result = build_star_comprehensive_alias_resolver().resolve(
        query(alias_text), as_of=AS_OF
    )
    assert result.unresolved is None
    assert result.relationship is TerminologyRelationship.EXACT_EQUIVALENT
    assert result.term is STAR_COMPREHENSIVE_COPAYMENT_TERM
    assert result.selected_concept is not None
    assert result.selected_concept.concept_family_id == "health:cost_sharing:copayment"


def test_alias_matching_is_case_and_whitespace_insensitive() -> None:
    result = build_star_comprehensive_alias_resolver().resolve(
        query("  CO   PAYMENT  "), as_of=AS_OF
    )
    assert result.unresolved is None
    assert result.term is STAR_COMPREHENSIVE_COPAYMENT_TERM


def test_unregistered_punctuation_variant_fails_closed() -> None:
    result = build_star_comprehensive_alias_resolver().resolve(
        query("co/pay"), as_of=AS_OF
    )
    assert result.unresolved is not None
    assert result.unresolved.reason_codes == ("NO_MATCHING_GOVERNED_TERM",)


def test_alias_does_not_cross_product_scope() -> None:
    scoped_query = replace(query("Copay"), product_id="another_product")
    result = build_star_comprehensive_alias_resolver().resolve(
        scoped_query, as_of=AS_OF
    )
    assert result.unresolved is not None


def test_direct_governed_term_still_resolves_without_alias_rewrite() -> None:
    result = build_star_comprehensive_alias_resolver().resolve(
        STAR_COMPREHENSIVE_COPAYMENT_TERM,
        as_of=AS_OF,
    )
    assert result.unresolved is None
    assert result.term is STAR_COMPREHENSIVE_COPAYMENT_TERM


def test_duplicate_alias_ids_are_rejected() -> None:
    snapshot = build_star_comprehensive_copayment_snapshot()
    alias = STAR_COMPREHENSIVE_COPAYMENT_ALIASES[0]
    with pytest.raises(TerminologyAliasError, match="alias_id values must be unique"):
        ExactAliasTerminologyResolver(
            resolver=snapshot.build_resolver(),
            aliases=(alias, alias),
        )


def test_alias_unknown_term_reference_is_rejected() -> None:
    snapshot = build_star_comprehensive_copayment_snapshot()
    alias = replace(
        STAR_COMPREHENSIVE_COPAYMENT_ALIASES[0],
        alias_id="alias:unknown",
        term_id="term:unknown",
    )
    with pytest.raises(TerminologyAliasError, match="unknown term_id"):
        ExactAliasTerminologyResolver(
            resolver=snapshot.build_resolver(),
            aliases=(alias,),
        )


def test_alias_requires_evidence() -> None:
    with pytest.raises(TerminologyAliasError, match="must contain evidence"):
        GovernedTerminologyAlias(
            alias_id="alias:test",
            alias_text="Test",
            term_id=STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id,
            insurer_id="star_health",
            product_id="star_comprehensive",
            product_variant_id=STAR_COMPREHENSIVE_COPAYMENT_TERM.product_variant_id,
            evidence_spans=(),
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.ELIGIBLE,
        )


def test_ineligible_alias_is_not_used() -> None:
    snapshot = build_star_comprehensive_copayment_snapshot()
    alias = replace(
        STAR_COMPREHENSIVE_COPAYMENT_ALIASES[0],
        review_status=TerminologyReviewStatus.DISCOVERED,
        publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
    )
    resolver = ExactAliasTerminologyResolver(
        resolver=snapshot.build_resolver(),
        aliases=(alias,),
    )
    result = resolver.resolve(query("Co pay"), as_of=AS_OF)
    assert result.unresolved is not None


def test_alias_evidence_values_are_typed() -> None:
    with pytest.raises(TerminologyAliasError, match="EvidenceSpan"):
        GovernedTerminologyAlias(
            alias_id="alias:test",
            alias_text="Test",
            term_id=STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id,
            insurer_id="star_health",
            product_id="star_comprehensive",
            product_variant_id=STAR_COMPREHENSIVE_COPAYMENT_TERM.product_variant_id,
            evidence_spans=("not-evidence",),  # type: ignore[arg-type]
            review_status=TerminologyReviewStatus.HUMAN_APPROVED,
            publication_status=TerminologyPublicationStatus.ELIGIBLE,
        )


def test_alias_records_preserve_policy_evidence() -> None:
    assert all(
        isinstance(alias.evidence_spans[0], EvidenceSpan)
        for alias in STAR_COMPREHENSIVE_COPAYMENT_ALIASES
    )
