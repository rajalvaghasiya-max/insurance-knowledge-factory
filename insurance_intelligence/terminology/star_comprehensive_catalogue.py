"""Governed Star Comprehensive terminology records for MO-024D.2.

This module publishes only the product-scoped copayment term and implementation
supported by the certified Star Comprehensive evidence chain. Deductible and
restoration records remain absent until equivalent governed product evidence is
available.
"""
from __future__ import annotations

from insurance_intelligence.contracts.terminology import (
    EvidenceSpan,
    InsurerMarketingTerm,
    ProductTermImplementation,
    TerminologyPublicationStatus,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.catalogue import INITIAL_CANONICAL_CONCEPTS
from insurance_intelligence.terminology.registry import TerminologyRegistrySnapshot


STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE = EvidenceSpan(
    source_id="source:star_health:star_comprehensive:policy_wording",
    document_id="star_health_star_comprehensive_policy_wording_v1",
    locator="page:39;chars:103605-107019",
    quoted_text=(
        "Co-payment: This policy is subject to co-payment of 10% of each and every "
        "claim amount for fresh as well as renewal policies for Insured Persons whose "
        "age at the time of entry is 61 years and above. This co-payment will not apply "
        "for those insured persons who have entered the policy before attaining 61 "
        "years of age and renew the policy continuously without any break. This "
        "co-payment is applicable for Sections II.1, II.2, II.3, II.4, II.5, II.6, "
        "II.7, II.8, II.9, II.10, II.11, II.15 and II.25."
    ),
    evidence_id="esp_67e4ab282ac7be61",
)


STAR_COMPREHENSIVE_COPAYMENT_TERM = InsurerMarketingTerm(
    term_id="term:star_health:star_comprehensive:copayment",
    display_name="Co-payment",
    insurer_id="star_health",
    product_id="star_comprehensive",
    product_variant_id="pv_star_health_star_comprehensive_shahlip26044v092526",
    effective_from=None,
    effective_to=None,
    evidence_spans=(STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE,),
    review_status=TerminologyReviewStatus.PUBLISHED,
    publication_status=TerminologyPublicationStatus.AUTHORITATIVE,
)


STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION = ProductTermImplementation(
    implementation_id="implementation:star_health:star_comprehensive:entry_age_61_copayment",
    term_id=STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id,
    concept_family_id="health:cost_sharing:copayment",
    behaviour_signature_id="ga_star_comprehensive_entry_age_61_conditional_copayment_v1",
    conditions=(
        "Applies to fresh and renewal policies when the insured person's age at entry is 61 years or above.",
        "Applies to each and every claim under Sections II.1-II.11, II.15 and II.25.",
    ),
    limitations=(
        "Does not apply when the insured person entered before age 61 and renews continuously without a break.",
        "The governed record does not extend the copayment beyond the policy sections expressly listed in the evidence.",
    ),
    evidence_spans=(STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE,),
    effective_from=None,
    effective_to=None,
)


def build_star_comprehensive_copayment_snapshot() -> TerminologyRegistrySnapshot:
    """Return the governed Star Comprehensive copayment registry snapshot."""
    return TerminologyRegistrySnapshot(
        marketing_terms=(STAR_COMPREHENSIVE_COPAYMENT_TERM,),
        implementations=(STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,),
        concepts=INITIAL_CANONICAL_CONCEPTS,
        alias_candidates=(),
    )


__all__ = [
    "STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE",
    "STAR_COMPREHENSIVE_COPAYMENT_TERM",
    "STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION",
    "build_star_comprehensive_copayment_snapshot",
]
