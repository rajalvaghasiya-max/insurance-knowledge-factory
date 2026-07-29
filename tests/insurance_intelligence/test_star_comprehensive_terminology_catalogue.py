from datetime import date

from insurance_intelligence.contracts.terminology import (
    TerminologyPublicationStatus,
    TerminologyRelationship,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.star_comprehensive_catalogue import (
    STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE,
    STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,
    STAR_COMPREHENSIVE_COPAYMENT_TERM,
    build_star_comprehensive_copayment_snapshot,
)


def test_star_copayment_term_is_authoritative_and_product_scoped() -> None:
    term = STAR_COMPREHENSIVE_COPAYMENT_TERM
    assert term.display_name == "Co-payment"
    assert term.insurer_id == "star_health"
    assert term.product_id == "star_comprehensive"
    assert term.product_variant_id == "pv_star_health_star_comprehensive_shahlip26044v092526"
    assert term.review_status is TerminologyReviewStatus.PUBLISHED
    assert term.publication_status is TerminologyPublicationStatus.AUTHORITATIVE


def test_star_copayment_evidence_preserves_source_locator_and_rule_text() -> None:
    evidence = STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE
    assert evidence.document_id == "star_health_star_comprehensive_policy_wording_v1"
    assert evidence.locator == "page:39;chars:103605-107019"
    assert evidence.evidence_id == "esp_67e4ab282ac7be61"
    assert "10% of each and every claim amount" in evidence.quoted_text
    assert "61 years and above" in evidence.quoted_text
    assert "renew the policy continuously without any break" in evidence.quoted_text
    assert "II.25" in evidence.quoted_text


def test_star_copayment_implementation_links_to_canonical_concept() -> None:
    implementation = STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION
    assert implementation.term_id == STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id
    assert implementation.concept_family_id == "health:cost_sharing:copayment"
    assert implementation.behaviour_signature_id == (
        "ga_star_comprehensive_entry_age_61_conditional_copayment_v1"
    )
    assert len(implementation.conditions) == 2
    assert len(implementation.limitations) == 2


def test_star_snapshot_contains_only_supported_product_term() -> None:
    snapshot = build_star_comprehensive_copayment_snapshot()
    assert snapshot.marketing_terms == (STAR_COMPREHENSIVE_COPAYMENT_TERM,)
    assert snapshot.implementations == (STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,)
    assert len(snapshot.concepts) == 3
    assert snapshot.alias_candidates == ()


def test_star_snapshot_resolves_exact_governed_term() -> None:
    snapshot = build_star_comprehensive_copayment_snapshot()
    result = snapshot.build_resolver().resolve(
        STAR_COMPREHENSIVE_COPAYMENT_TERM,
        as_of=date(2026, 7, 29),
    )
    assert result.relationship is TerminologyRelationship.EXACT_EQUIVALENT
    assert result.selected_concept is not None
    assert result.selected_concept.concept_family_id == "health:cost_sharing:copayment"
    assert result.implementation == STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION
    assert result.publication_status is TerminologyPublicationStatus.AUTHORITATIVE


def test_star_snapshot_does_not_invent_deductible_or_restoration_terms() -> None:
    snapshot = build_star_comprehensive_copayment_snapshot()
    concept_ids = {item.concept_family_id for item in snapshot.concepts}
    term_names = {item.display_name for item in snapshot.marketing_terms}
    assert "health:cost_sharing:deductible" in concept_ids
    assert "health:coverage_capacity:restoration_benefit" in concept_ids
    assert term_names == {"Co-payment"}
