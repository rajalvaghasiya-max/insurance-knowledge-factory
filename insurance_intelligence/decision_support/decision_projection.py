"""Set-relative, education-first personalized decision projection for MO-027H.

This layer renders governed per-product alignments, interaction units, protection
floors, hard-constraint outcomes, unknowns, and set-level limitations. It is
strictly non-verdict: it never aggregates alignments into a net lean, winner,
ranking, suitability conclusion, or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import DecisionRole
from insurance_intelligence.decision_support.decision_sufficiency import (
    DecisionSufficiencyDecision,
    DecisionSufficiencyStatus,
    ProductConstraintStatus,
    ProductDecisionEvidence,
)
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentFinding,
    DimensionAlignmentStatus,
)
from insurance_intelligence.decision_support.interaction_clusters import (
    InteractionDecisionUnit,
)


class DecisionProjectionError(ValueError):
    """Raised when an MO-027H projection violates an education-first invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionProjectionError(f"{field_name} must be non-empty text")
    return value.strip()


def _typed_tuple(values: tuple, expected_type: type, field_name: str) -> tuple:
    if not isinstance(values, tuple) or not all(type(item) is expected_type for item in values):
        raise DecisionProjectionError(
            f"{field_name} must contain exact {expected_type.__name__} values"
        )
    return values


class DecisionProjectionStatus(str, Enum):
    READY = "READY"
    READY_WITH_LIMITATIONS = "READY_WITH_LIMITATIONS"
    ACTION_REQUIRED = "ACTION_REQUIRED"


@dataclass(frozen=True)
class ProductDecisionProjection:
    product_reference: str
    alignments: tuple[DimensionAlignmentFinding, ...]
    protection_floor_findings: tuple[DimensionAlignmentFinding, ...]
    unresolved_findings: tuple[DimensionAlignmentFinding, ...]
    interaction_units: tuple[InteractionDecisionUnit, ...]
    failed_constraint_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "product_reference",
            _required_text(self.product_reference, "product_reference"),
        )
        _typed_tuple(self.alignments, DimensionAlignmentFinding, "alignments")
        _typed_tuple(
            self.protection_floor_findings,
            DimensionAlignmentFinding,
            "protection_floor_findings",
        )
        _typed_tuple(self.unresolved_findings, DimensionAlignmentFinding, "unresolved_findings")
        _typed_tuple(self.interaction_units, InteractionDecisionUnit, "interaction_units")
        if any(item.product_reference != self.product_reference for item in self.alignments):
            raise DecisionProjectionError("all alignments must belong to product_reference")
        if any(item.product_reference != self.product_reference for item in self.interaction_units):
            raise DecisionProjectionError("all interaction units must belong to product_reference")
        expected_floors = tuple(
            item for item in self.alignments if item.decision_role is DecisionRole.PROTECTION_FLOOR
        )
        if self.protection_floor_findings != expected_floors:
            raise DecisionProjectionError(
                "protection_floor_findings must preserve every protection-floor alignment"
            )
        expected_unresolved = tuple(
            item for item in self.alignments if item.status is DimensionAlignmentStatus.UNRESOLVED
        )
        if self.unresolved_findings != expected_unresolved:
            raise DecisionProjectionError(
                "unresolved_findings must exactly preserve unresolved alignments"
            )
        if not isinstance(self.failed_constraint_ids, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.failed_constraint_ids
        ):
            raise DecisionProjectionError("failed_constraint_ids must contain non-empty text")
        if len(self.failed_constraint_ids) != len(set(self.failed_constraint_ids)):
            raise DecisionProjectionError("failed_constraint_ids must not contain duplicates")


@dataclass(frozen=True)
class GovernedDecisionSupportProjection:
    projection_id: str
    sufficiency_decision_id: str
    status: DecisionProjectionStatus
    left: ProductDecisionProjection
    right: ProductDecisionProjection
    set_scope_statement: str
    decision_boundary: str
    limitations: tuple[str, ...]
    blocking_reference_ids: tuple[str, ...]
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in (
            "projection_id",
            "sufficiency_decision_id",
            "set_scope_statement",
            "decision_boundary",
            "contract_version",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if not isinstance(self.status, DecisionProjectionStatus):
            raise DecisionProjectionError("status must be a DecisionProjectionStatus")
        if type(self.left) is not ProductDecisionProjection or type(self.right) is not ProductDecisionProjection:
            raise DecisionProjectionError("left and right must be exact ProductDecisionProjection values")
        if self.left.product_reference == self.right.product_reference:
            raise DecisionProjectionError("projection requires two different products")
        if "among the compared products" not in self.set_scope_statement.lower():
            raise DecisionProjectionError("set_scope_statement must make comparison-set scope explicit")
        boundary_lower = self.decision_boundary.lower()
        forbidden_required_absence = ("winner", "recommend", "more suitable", "leans toward")
        if any(term in boundary_lower for term in forbidden_required_absence):
            raise DecisionProjectionError("decision_boundary must not contain product-verdict language")
        if "does not choose" not in boundary_lower or "user decides" not in boundary_lower:
            raise DecisionProjectionError(
                "decision_boundary must state that the projection does not choose and the user decides"
            )
        for field_name in ("limitations", "blocking_reference_ids"):
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or not all(isinstance(item, str) and item.strip() for item in values):
                raise DecisionProjectionError(f"{field_name} must contain non-empty text")
            if len(values) != len(set(values)):
                raise DecisionProjectionError(f"{field_name} must not contain duplicates")


def _project_product(evidence: ProductDecisionEvidence) -> ProductDecisionProjection:
    return ProductDecisionProjection(
        product_reference=evidence.product_reference,
        alignments=evidence.alignments,
        protection_floor_findings=tuple(
            item for item in evidence.alignments if item.decision_role is DecisionRole.PROTECTION_FLOOR
        ),
        unresolved_findings=tuple(
            item for item in evidence.alignments if item.status is DimensionAlignmentStatus.UNRESOLVED
        ),
        interaction_units=evidence.interaction_units,
        failed_constraint_ids=(
            evidence.failed_constraint_ids
            if evidence.constraint_status is ProductConstraintStatus.FAILS_ONE_OR_MORE
            else ()
        ),
    )


def project_decision_support(
    *,
    projection_id: str,
    sufficiency: DecisionSufficiencyDecision,
    left: ProductDecisionEvidence,
    right: ProductDecisionEvidence,
) -> GovernedDecisionSupportProjection:
    """Project non-verdict personalized decision support over exactly two compared products."""

    if type(sufficiency) is not DecisionSufficiencyDecision:
        raise DecisionProjectionError("sufficiency must be exact DecisionSufficiencyDecision")
    if type(left) is not ProductDecisionEvidence or type(right) is not ProductDecisionEvidence:
        raise DecisionProjectionError("left and right must be exact ProductDecisionEvidence values")
    if sufficiency.left_product_reference != left.product_reference:
        raise DecisionProjectionError("left product must match sufficiency decision")
    if sufficiency.right_product_reference != right.product_reference:
        raise DecisionProjectionError("right product must match sufficiency decision")

    action_required = {
        DecisionSufficiencyStatus.MORE_CUSTOMER_CONTEXT_REQUIRED,
        DecisionSufficiencyStatus.BLOCKED_BY_PRODUCT_UNKNOWN,
        DecisionSufficiencyStatus.NEITHER_MEETS_HARD_CONSTRAINTS,
        DecisionSufficiencyStatus.SET_MAY_BE_INADEQUATE,
    }
    limited = {
        DecisionSufficiencyStatus.DECISION_SUPPORT_READY_WITH_LIMITATIONS,
        DecisionSufficiencyStatus.BOTH_HAVE_MATERIAL_CONCERNS,
    }
    if sufficiency.status in action_required:
        status = DecisionProjectionStatus.ACTION_REQUIRED
    elif sufficiency.status in limited:
        status = DecisionProjectionStatus.READY_WITH_LIMITATIONS
    else:
        status = DecisionProjectionStatus.READY

    return GovernedDecisionSupportProjection(
        projection_id=projection_id,
        sufficiency_decision_id=sufficiency.decision_id,
        status=status,
        left=_project_product(left),
        right=_project_product(right),
        set_scope_statement=(
            "This decision aid is limited to the governed evidence available among the compared products; "
            "it is not a statement about every product available in the market."
        ),
        decision_boundary=(
            "This projection explains how each compared product aligns or conflicts with declared customer priorities, "
            "while preserving protection floors, interactions, hard constraints, and unknowns. It does not choose a product; the user decides."
        ),
        limitations=sufficiency.reasons,
        blocking_reference_ids=sufficiency.blocking_reference_ids,
    )


__all__ = [
    "DecisionProjectionError",
    "DecisionProjectionStatus",
    "GovernedDecisionSupportProjection",
    "ProductDecisionProjection",
    "project_decision_support",
]
