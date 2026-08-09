"""Controlled exact aliases for Star Comprehensive copayment terminology."""
from __future__ import annotations

from insurance_intelligence.contracts.terminology import (
    TerminologyPublicationStatus,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.alias_resolver import (
    ExactAliasTerminologyResolver,
    GovernedTerminologyAlias,
)
from insurance_intelligence.terminology.star_comprehensive_catalogue import (
    STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE,
    STAR_COMPREHENSIVE_COPAYMENT_TERM,
    build_star_comprehensive_copayment_snapshot,
)

_VARIANT_ID = "pv_star_health_star_comprehensive_shahlip26044v092526"


def _alias(alias_id: str, alias_text: str) -> GovernedTerminologyAlias:
    return GovernedTerminologyAlias(
        alias_id=alias_id,
        alias_text=alias_text,
        term_id=STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id,
        insurer_id="star_health",
        product_id="star_comprehensive",
        product_variant_id=_VARIANT_ID,
        evidence_spans=(STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE,),
        review_status=TerminologyReviewStatus.HUMAN_APPROVED,
        publication_status=TerminologyPublicationStatus.ELIGIBLE,
    )


STAR_COMPREHENSIVE_COPAYMENT_ALIASES = (
    _alias("alias:star_health:star_comprehensive:co_pay", "Co pay"),
    _alias("alias:star_health:star_comprehensive:co_payment", "Co payment"),
    _alias("alias:star_health:star_comprehensive:copay", "Copay"),
)


def build_star_comprehensive_alias_resolver() -> ExactAliasTerminologyResolver:
    """Return the controlled exact-alias resolver for Star copayment terminology."""
    snapshot = build_star_comprehensive_copayment_snapshot()
    return ExactAliasTerminologyResolver(
        resolver=snapshot.build_resolver(),
        aliases=STAR_COMPREHENSIVE_COPAYMENT_ALIASES,
    )


__all__ = [
    "STAR_COMPREHENSIVE_COPAYMENT_ALIASES",
    "build_star_comprehensive_alias_resolver",
]
