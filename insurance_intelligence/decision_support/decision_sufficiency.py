"""Decision sufficiency and comparison-set adequacy gate for MO-027G.

This layer decides whether education-first personalized decision support may be
presented safely. It does not choose a product. It consumes already-governed local
alignment findings, interaction decision units, explicit hard-constraint outcomes,
and set-level adequacy signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import DecisionRole
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentFinding,
    DimensionAlignmentStatus,
)
from insurance_intelligence.decision_support.interaction_clusters import (
    InteractionDecisionUnit,
    InteractionDecisionUnitStatus,
)


class DecisionSufficiencyError(ValueError):
    """Raised when a decision-sufficiency input violates a governance invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionSufficiencyError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise DecisionSufficiencyError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(item, f"{field_name}[]") for item in values)
    if len(cleaned) != len(set(cleaned)):
        raise DecisionSufficiencyError(f"{field_name} must not contain duplicates")
    return cleaned


class ProductConstraintStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    SATISFIES_ALL = "SATISFIES_ALL"
    FAILS_ONE_OR_MORE = "FAILS_ONE_OR_MORE"


class SetAdequacySignal(str, Enum):
    NO_SET_CONCERN = "NO_SET_CONCERN"
    SHARED_MATERIAL_WEAKNESS = "SHARED_MATERIAL_WEAKNESS"
    MATERIAL_DIMENSION_MISSING_ACROSS_SET = "MATERIAL_DIMENSION_MISSING_ACROSS_SET"


class DecisionSufficiencyStatus(str, Enum):
    DECISION_SUPPORT_READY = "DECISION_SUPPORT_READY"
    DECISION_SUPPORT_READY_WITH_LIMITATIONS = "DECISION_SUPPORT_READY_WITH_LIMITATIONS"
    MORE_CUSTOMER_CONTEXT_REQUIRED = "MORE_CUSTOMER_CONTEXT_REQUIRED"
    BLOCKED_BY_PRODUCT_UNKNOWN = "BLOCKED_BY_PRODUCT_UNKNOWN"
    BOTH_HAVE_MATERIAL_CONCERNS = "BOTH_HAVE_MATERIAL_CONCERNS"
    NEITHER_MEETS_HARD_CONSTRAINTS = "NEITHER_MEETS_HARD_CONSTRAINTS"
    SET_MAY_BE_INADEQUATE = "SET_MAY_BE_INADEQUATE"


@dataclass(frozen=True)
class ProductDecisionEvidence:
    product_reference: str
    alignments: tuple[DimensionAlignmentFinding, ...]
    interaction_units: tuple[InteractionDecisionUnit, ...] = ()
    constraint_status: ProductConstraintStatus = ProductConstraintStatus.NOT_EVALUATED
    failed_constraint_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "product_reference", _required_text(self.product_reference, "product_reference"))
        if not isinstance(self.alignments, tuple) or not self.alignments:
            raise DecisionSufficiencyError("alignments must be a non-empty tuple")
        if not all(type(item) is DimensionAlignmentFinding for item in self.alignments):
            raise DecisionSufficiencyError("alignments must contain exact DimensionAlignmentFinding values")
        if any(item.product_reference != self.product_reference for item in self.alignments):
            raise DecisionSufficiencyError("all alignments must belong to product_reference")
        ids = tuple(item.dimension_id for item in self.alignments)
        if len(ids) != len(set(ids)):
            raise DecisionSufficiencyError("alignments must not duplicate dimensions")
        if not isinstance(self.interaction_units, tuple) or not all(
            type(item) is InteractionDecisionUnit for item in self.interaction_units
        ):
            raise DecisionSufficiencyError("interaction_units must contain exact InteractionDecisionUnit values")
        if any(item.product_reference != self.product_reference for item in self.interaction_units):
            raise DecisionSufficiencyError("interaction units must belong to product_reference")
        if not isinstance(self.constraint_status, ProductConstraintStatus):
            raise DecisionSufficiencyError("constraint_status must be a ProductConstraintStatus")
        object.__setattr__(self, "failed_constraint_ids", _text_tuple(self.failed_constraint_ids, "failed_constraint_ids"))
        if self.constraint_status is ProductConstraintStatus.FAILS_ONE_OR_MORE and not self.failed_constraint_ids:
            raise DecisionSufficiencyError("failing constraint status requires failed_constraint_ids")
        if self.constraint_status is not ProductConstraintStatus.FAILS_ONE_OR_MORE and self.failed_constraint_ids:
            raise DecisionSufficiencyError("failed_constraint_ids require FAILS_ONE_OR_MORE status")

    @property
    def has_product_unknown(self) -> bool:
        return any(item.status is DimensionAlignmentStatus.UNRESOLVED for item in self.alignments)

    @property
    def has_material_concern(self) -> bool:
        concerning = {
            DimensionAlignmentStatus.CONFLICTS,
            DimensionAlignmentStatus.STRONGLY_CONFLICTS,
            DimensionAlignmentStatus.PROTECTION_FLOOR_UNPRIORITIZED,
            DimensionAlignmentStatus.UNRESOLVED,
        }
        return any(
            item.status in concerning
            or (
                item.decision_role is DecisionRole.PROTECTION_FLOOR
                and item.status is not DimensionAlignmentStatus.NOT_APPLICABLE
                and item.status not in {
                    DimensionAlignmentStatus.STRONGLY_ALIGNS,
                    DimensionAlignmentStatus.ALIGNS,
                    DimensionAlignmentStatus.NEUTRAL,
                }
            )
            for item in self.alignments
        ) or any(
            item.status is InteractionDecisionUnitStatus.INCOMPLETE_LINKED_DIMENSION
            for item in self.interaction_units
        )

    @property
    def has_incomplete_interaction(self) -> bool:
        return any(
            item.status is InteractionDecisionUnitStatus.INCOMPLETE_LINKED_DIMENSION
            for item in self.interaction_units
        )


@dataclass(frozen=True)
class DecisionSufficiencyDecision:
    decision_id: str
    status: DecisionSufficiencyStatus
    left_product_reference: str
    right_product_reference: str
    reasons: tuple[str, ...]
    blocking_reference_ids: tuple[str, ...] = ()
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in (
            "decision_id",
            "left_product_reference",
            "right_product_reference",
            "contract_version",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if self.left_product_reference == self.right_product_reference:
            raise DecisionSufficiencyError("decision requires two different products")
        if not isinstance(self.status, DecisionSufficiencyStatus):
            raise DecisionSufficiencyError("status must be a DecisionSufficiencyStatus")
        object.__setattr__(self, "reasons", _text_tuple(self.reasons, "reasons"))
        if not self.reasons:
            raise DecisionSufficiencyError("reasons must not be empty")
        object.__setattr__(
            self,
            "blocking_reference_ids",
            _text_tuple(self.blocking_reference_ids, "blocking_reference_ids"),
        )


def evaluate_decision_sufficiency(
    *,
    decision_id: str,
    left: ProductDecisionEvidence,
    right: ProductDecisionEvidence,
    pending_material_question_ids: tuple[str, ...] = (),
    set_adequacy_signals: tuple[SetAdequacySignal, ...] = (),
) -> DecisionSufficiencyDecision:
    """Evaluate whether decision support is ready without producing a product verdict."""

    if type(left) is not ProductDecisionEvidence or type(right) is not ProductDecisionEvidence:
        raise DecisionSufficiencyError("left and right must be exact ProductDecisionEvidence values")
    if left.product_reference == right.product_reference:
        raise DecisionSufficiencyError("cannot evaluate the same product against itself")
    pending_material_question_ids = _text_tuple(
        pending_material_question_ids, "pending_material_question_ids"
    )
    if not isinstance(set_adequacy_signals, tuple) or not all(
        isinstance(item, SetAdequacySignal) for item in set_adequacy_signals
    ):
        raise DecisionSufficiencyError("set_adequacy_signals must contain SetAdequacySignal values")
    if len(set_adequacy_signals) != len(set(set_adequacy_signals)):
        raise DecisionSufficiencyError("set_adequacy_signals must not contain duplicates")

    # Explicit hard constraints dominate softer decision-support readiness.
    if (
        left.constraint_status is ProductConstraintStatus.FAILS_ONE_OR_MORE
        and right.constraint_status is ProductConstraintStatus.FAILS_ONE_OR_MORE
    ):
        refs = left.failed_constraint_ids + tuple(
            item for item in right.failed_constraint_ids if item not in left.failed_constraint_ids
        )
        return DecisionSufficiencyDecision(
            decision_id=decision_id,
            status=DecisionSufficiencyStatus.NEITHER_MEETS_HARD_CONSTRAINTS,
            left_product_reference=left.product_reference,
            right_product_reference=right.product_reference,
            reasons=("Neither compared product satisfies all actionable user-declared hard constraints.",),
            blocking_reference_ids=refs,
        )

    if pending_material_question_ids:
        return DecisionSufficiencyDecision(
            decision_id=decision_id,
            status=DecisionSufficiencyStatus.MORE_CUSTOMER_CONTEXT_REQUIRED,
            left_product_reference=left.product_reference,
            right_product_reference=right.product_reference,
            reasons=("One or more material customer questions remain unresolved.",),
            blocking_reference_ids=pending_material_question_ids,
        )

    if left.has_product_unknown or right.has_product_unknown:
        refs = tuple(
            sorted(
                item.finding_id
                for evidence in (left, right)
                for item in evidence.alignments
                if item.status is DimensionAlignmentStatus.UNRESOLVED
            )
        )
        return DecisionSufficiencyDecision(
            decision_id=decision_id,
            status=DecisionSufficiencyStatus.BLOCKED_BY_PRODUCT_UNKNOWN,
            left_product_reference=left.product_reference,
            right_product_reference=right.product_reference,
            reasons=("At least one material product dimension remains unresolved on the governed evidence available.",),
            blocking_reference_ids=refs,
        )

    nontrivial_set_signals = tuple(
        item for item in set_adequacy_signals if item is not SetAdequacySignal.NO_SET_CONCERN
    )
    if nontrivial_set_signals:
        return DecisionSufficiencyDecision(
            decision_id=decision_id,
            status=DecisionSufficiencyStatus.SET_MAY_BE_INADEQUATE,
            left_product_reference=left.product_reference,
            right_product_reference=right.product_reference,
            reasons=(
                "The current comparison set has a material shared weakness or missing dimension and should not be presented as exhaustive of suitable alternatives.",
            ),
            blocking_reference_ids=tuple(item.value for item in nontrivial_set_signals),
        )

    if left.has_material_concern and right.has_material_concern:
        return DecisionSufficiencyDecision(
            decision_id=decision_id,
            status=DecisionSufficiencyStatus.BOTH_HAVE_MATERIAL_CONCERNS,
            left_product_reference=left.product_reference,
            right_product_reference=right.product_reference,
            reasons=("Both compared products contain at least one material concern that must remain visible in decision support.",),
        )

    if left.has_incomplete_interaction or right.has_incomplete_interaction:
        return DecisionSufficiencyDecision(
            decision_id=decision_id,
            status=DecisionSufficiencyStatus.DECISION_SUPPORT_READY_WITH_LIMITATIONS,
            left_product_reference=left.product_reference,
            right_product_reference=right.product_reference,
            reasons=("Decision support may be presented, but at least one governed interaction unit is incomplete.",),
        )

    return DecisionSufficiencyDecision(
        decision_id=decision_id,
        status=DecisionSufficiencyStatus.DECISION_SUPPORT_READY,
        left_product_reference=left.product_reference,
        right_product_reference=right.product_reference,
        reasons=("The available governed product and customer context is sufficient for non-verdict decision support.",),
    )


__all__ = [
    "DecisionSufficiencyDecision",
    "DecisionSufficiencyError",
    "DecisionSufficiencyStatus",
    "ProductConstraintStatus",
    "ProductDecisionEvidence",
    "SetAdequacySignal",
    "evaluate_decision_sufficiency",
]
