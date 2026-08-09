"""Governed MO-026C policy metadata for copayment assessment."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus


@dataclass(frozen=True)
class CopaymentAssessmentPolicy:
    policy_id: str
    policy_version: str
    governance_basis: str
    review_status: ReviewStatus
    publication_status: PublicationStatus
    effective_from: date

    @property
    def is_governed_for_use(self) -> bool:
        return (
            self.review_status is ReviewStatus.APPROVED
            and self.publication_status is PublicationStatus.PUBLISHED
        )


COPAYMENT_ASSESSMENT_POLICY = CopaymentAssessmentPolicy(
    policy_id="assessment_policy:health:copayment:v1",
    policy_version="1.0",
    governance_basis=(
        "Education-first protection-floor policy choice. Zero copayment is very strong on this dimension. "
        "Any non-zero copayment is a material cost-sharing restriction; up to and including 20 percent is "
        "restrictive and amounts above 20 percent are very restrictive. The band describes only the intrinsic "
        "restriction and never overrides trigger, exception, scope, or product-level trade-offs."
    ),
    review_status=ReviewStatus.APPROVED,
    publication_status=PublicationStatus.PUBLISHED,
    effective_from=date(2026, 8, 9),
)


__all__ = ["COPAYMENT_ASSESSMENT_POLICY", "CopaymentAssessmentPolicy"]
