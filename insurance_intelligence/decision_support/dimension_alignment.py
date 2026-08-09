"""Interaction-aware per-dimension customer alignment for MO-027F.

This layer relates one governed MO-026 assessment to an explicitly actionable
customer priority on the same dimension. It never aggregates dimensions into a
net direction. Protection-floor dimensions remain visible even when the customer
has not declared a corresponding priority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    BenefitInteractionReference,
    DecisionRole,
)
from insurance_intelligence.decision_support.customer_context import CustomerPriority


class DimensionAlignmentError(ValueError):
    """Raised when customer alignment violates a governance invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DimensionAlignmentError(f"{field_name} must be non-empty text")
    return value.strip()


class DimensionAlignmentStatus(str, Enum):
    STRONGLY_ALIGNS = "STRONGLY_ALIGNS"
    ALIGNS = "ALIGNS"
    NEUTRAL = "NEUTRAL"
    CONFLICTS = "CONFLICTS"
    STRONGLY_CONFLICTS = "STRONGLY_CONFLICTS"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_DECLARED_PRIORITY = "NO_DECLARED_PRIORITY"
    PROTECTION_FLOOR_UNPRIORITIZED = "PROTECTION_FLOOR_UNPRIORITIZED"


_BAND_TO_ALIGNMENT = {
    AssessmentBand.VERY_STRONG: DimensionAlignmentStatus.STRONGLY_ALIGNS,
    AssessmentBand.STRONG: DimensionAlignmentStatus.ALIGNS,
    AssessmentBand.MODERATE: DimensionAlignmentStatus.NEUTRAL,
    AssessmentBand.RESTRICTIVE: DimensionAlignmentStatus.CONFLICTS,
    AssessmentBand.VERY_RESTRICTIVE: DimensionAlignmentStatus.STRONGLY_CONFLICTS,
}


@dataclass(frozen=True)
class DimensionAlignmentFinding:
    finding_id: str
    product_reference: str
    dimension_id: str
    decision_role: DecisionRole
    assessment: BenefitAssessment
    customer_priority: CustomerPriority | None
    status: DimensionAlignmentStatus
    explanation: str
    interaction_references: tuple[BenefitInteractionReference, ...]
    limitations: tuple[str, ...] = ()
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in (
            "finding_id",
            "product_reference",
            "dimension_id",
            "explanation",
            "contract_version",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if type(self.assessment) is not BenefitAssessment:
            raise DimensionAlignmentError("assessment must be the exact BenefitAssessment type")
        if self.assessment.dimension_id != self.dimension_id:
            raise DimensionAlignmentError("assessment dimension must match finding dimension")
        if self.assessment.decision_role is not self.decision_role:
            raise DimensionAlignmentError("assessment decision role must match finding role")
        if self.customer_priority is not None:
            if type(self.customer_priority) is not CustomerPriority:
                raise DimensionAlignmentError("customer_priority must be exact CustomerPriority or None")
            if self.customer_priority.dimension_id != self.dimension_id:
                raise DimensionAlignmentError("customer priority dimension must match finding dimension")
            if not self.customer_priority.is_materially_actionable:
                raise DimensionAlignmentError("inferred customer priority cannot drive material alignment")
        if not isinstance(self.status, DimensionAlignmentStatus):
            raise DimensionAlignmentError("status must be a DimensionAlignmentStatus")
        if not isinstance(self.decision_role, DecisionRole):
            raise DimensionAlignmentError("decision_role must be a DecisionRole")
        if not isinstance(self.interaction_references, tuple) or not all(
            isinstance(item, BenefitInteractionReference) for item in self.interaction_references
        ):
            raise DimensionAlignmentError("interaction_references must contain BenefitInteractionReference values")
        if self.interaction_references != self.assessment.interaction_references:
            raise DimensionAlignmentError("alignment must preserve assessment interactions unchanged")
        if not isinstance(self.limitations, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.limitations
        ):
            raise DimensionAlignmentError("limitations must contain non-empty text values")

        if self.decision_role is DecisionRole.PROTECTION_FLOOR and self.status is DimensionAlignmentStatus.NO_DECLARED_PRIORITY:
            raise DimensionAlignmentError("protection-floor dimensions cannot be hidden as no declared priority")
        if self.status is DimensionAlignmentStatus.PROTECTION_FLOOR_UNPRIORITIZED and self.decision_role is not DecisionRole.PROTECTION_FLOOR:
            raise DimensionAlignmentError("only protection-floor dimensions may use PROTECTION_FLOOR_UNPRIORITIZED")

    @property
    def has_material_interaction(self) -> bool:
        return self.assessment.has_material_interaction


def align_assessment_to_customer_priority(
    *,
    finding_id: str,
    product_reference: str,
    assessment: BenefitAssessment,
    customer_priority: CustomerPriority | None,
) -> DimensionAlignmentFinding:
    """Align one governed dimension to one explicit customer priority without aggregation."""

    if type(assessment) is not BenefitAssessment:
        raise DimensionAlignmentError("assessment must be the exact BenefitAssessment type")
    if customer_priority is not None:
        if type(customer_priority) is not CustomerPriority:
            raise DimensionAlignmentError("customer_priority must be exact CustomerPriority or None")
        if customer_priority.dimension_id != assessment.dimension_id:
            raise DimensionAlignmentError("customer priority must target the same dimension")
        if not customer_priority.is_materially_actionable:
            raise DimensionAlignmentError("inferred customer priority must be confirmed before alignment")

    if assessment.status is AssessmentStatus.NOT_SCORABLE:
        status = DimensionAlignmentStatus.UNRESOLVED
        explanation = "The product dimension is unresolved, so no customer-alignment conclusion is permitted."
    elif assessment.status is AssessmentStatus.NOT_APPLICABLE:
        status = DimensionAlignmentStatus.NOT_APPLICABLE
        explanation = "The governed product assessment marks this dimension not applicable."
    elif customer_priority is None:
        if assessment.decision_role is DecisionRole.PROTECTION_FLOOR:
            status = DimensionAlignmentStatus.PROTECTION_FLOOR_UNPRIORITIZED
            explanation = (
                "No customer priority was declared for this protection-floor dimension, but the dimension remains visible and must not be suppressed."
            )
        else:
            status = DimensionAlignmentStatus.NO_DECLARED_PRIORITY
            explanation = "No actionable customer priority has been declared for this dimension."
    else:
        assert assessment.assessment_band is not None
        status = _BAND_TO_ALIGNMENT[assessment.assessment_band]
        explanation = (
            f"The customer's declared priority for {assessment.dimension_id} is evaluated against the governed product assessment band {assessment.assessment_band.value}; "
            f"the resulting local alignment is {status.value}."
        )

    limitations = assessment.limitations
    if assessment.has_material_interaction:
        limitations = limitations + (
            "This dimension has a material or critical governed interaction and must not be interpreted independently of the linked dimension(s).",
        )

    return DimensionAlignmentFinding(
        finding_id=finding_id,
        product_reference=product_reference,
        dimension_id=assessment.dimension_id,
        decision_role=assessment.decision_role,
        assessment=assessment,
        customer_priority=customer_priority,
        status=status,
        explanation=explanation,
        interaction_references=assessment.interaction_references,
        limitations=limitations,
    )


__all__ = [
    "DimensionAlignmentError",
    "DimensionAlignmentFinding",
    "DimensionAlignmentStatus",
    "align_assessment_to_customer_priority",
]
