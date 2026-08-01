"""Static governed benefit registry for MO-025E.

The registry exposes approved catalogue entries only. It does not perform
comparison, ranking, recommendation, entitlement, or customer-answer logic.
"""
from __future__ import annotations

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.contracts import ProductBenefitImplementation
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)

GOVERNED_BENEFIT_IMPLEMENTATIONS: tuple[ProductBenefitImplementation, ...] = (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


def registered_benefit_implementations() -> tuple[ProductBenefitImplementation, ...]:
    """Return the immutable registry snapshot in deterministic identity order."""

    return tuple(
        sorted(
            GOVERNED_BENEFIT_IMPLEMENTATIONS,
            key=lambda item: (
                item.concept_id,
                item.insurer_id,
                item.product_id,
                item.product_variant_id,
                item.implementation_id,
            ),
        )
    )


__all__ = [
    "GOVERNED_BENEFIT_IMPLEMENTATIONS",
    "registered_benefit_implementations",
]
