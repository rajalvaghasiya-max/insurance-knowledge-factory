"""Deterministic material-question planning for MO-027E.

A question is admissible only when it is tied to a traceable decision-relevant
trigger. The planner does not run a generic proposal-form questionnaire and does
not infer what a customer should value.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.decision_support.customer_context import (
    CustomerDecisionContext,
)
from insurance_intelligence.decision_support.personalization_boundary import (
    CustomerContextAccess,
    PersonalizationBoundaryDecision,
)


class MaterialQuestionPlannerError(ValueError):
    """Raised when question planning violates a governance invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MaterialQuestionPlannerError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise MaterialQuestionPlannerError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(value, f"{field_name}[]") for value in values)
    if not allow_empty and not cleaned:
        raise MaterialQuestionPlannerError(f"{field_name} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise MaterialQuestionPlannerError(f"{field_name} must not contain duplicates")
    return cleaned


class QuestionTriggerType(str, Enum):
    PENDING_CIRCUMSTANCE_CONFIRMATION = "PENDING_CIRCUMSTANCE_CONFIRMATION"
    PENDING_PRIORITY_CONFIRMATION = "PENDING_PRIORITY_CONFIRMATION"
    UNRESOLVED_COMPARISON_DIMENSION = "UNRESOLVED_COMPARISON_DIMENSION"
    GOVERNED_APPLICABILITY_DEPENDENCY = "GOVERNED_APPLICABILITY_DEPENDENCY"
    DECLARED_HARD_CONSTRAINT_CLARIFICATION = "DECLARED_HARD_CONSTRAINT_CLARIFICATION"


class MaterialQuestionPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"


_PRIORITY_ORDER = {
    MaterialQuestionPriority.CRITICAL: 0,
    MaterialQuestionPriority.HIGH: 1,
    MaterialQuestionPriority.NORMAL: 2,
}


@dataclass(frozen=True)
class MaterialQuestionCandidate:
    question_id: str
    trigger_type: QuestionTriggerType
    prompt: str
    target_input_id: str
    material_dimension_ids: tuple[str, ...]
    trigger_reference_ids: tuple[str, ...]
    priority: MaterialQuestionPriority
    why_material: str

    def __post_init__(self) -> None:
        for field_name in ("question_id", "prompt", "target_input_id", "why_material"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.trigger_type, QuestionTriggerType):
            raise MaterialQuestionPlannerError("trigger_type must be a QuestionTriggerType")
        if not isinstance(self.priority, MaterialQuestionPriority):
            raise MaterialQuestionPlannerError("priority must be a MaterialQuestionPriority")
        object.__setattr__(
            self,
            "material_dimension_ids",
            _text_tuple(self.material_dimension_ids, "material_dimension_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "trigger_reference_ids",
            _text_tuple(self.trigger_reference_ids, "trigger_reference_ids", allow_empty=False),
        )


@dataclass(frozen=True)
class MaterialQuestionPlan:
    plan_id: str
    customer_context_id: str
    questions: tuple[MaterialQuestionCandidate, ...]
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in ("plan_id", "customer_context_id", "contract_version"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.questions, tuple):
            raise MaterialQuestionPlannerError("questions must be a tuple")
        if not all(type(item) is MaterialQuestionCandidate for item in self.questions):
            raise MaterialQuestionPlannerError(
                "questions must contain exact MaterialQuestionCandidate values"
            )
        ids = tuple(item.question_id for item in self.questions)
        if len(ids) != len(set(ids)):
            raise MaterialQuestionPlannerError("questions must not contain duplicate question ids")
        targets = tuple(item.target_input_id for item in self.questions)
        if len(targets) != len(set(targets)):
            raise MaterialQuestionPlannerError(
                "question plan must not ask multiple questions for the same target input"
            )
        ordered = tuple(
            sorted(
                self.questions,
                key=lambda item: (
                    _PRIORITY_ORDER[item.priority],
                    item.question_id,
                ),
            )
        )
        object.__setattr__(self, "questions", ordered)

    @property
    def has_questions(self) -> bool:
        return bool(self.questions)


def _validate_confirmation_candidate(
    *,
    candidate: MaterialQuestionCandidate,
    context: CustomerDecisionContext,
) -> None:
    if candidate.trigger_type is QuestionTriggerType.PENDING_CIRCUMSTANCE_CONFIRMATION:
        valid_targets = {
            f"circumstance:{item.subject_reference}:{item.circumstance_id}"
            for item in context.pending_circumstance_confirmations
        }
        if candidate.target_input_id not in valid_targets:
            raise MaterialQuestionPlannerError(
                "circumstance-confirmation question must target a pending inferred circumstance"
            )
    elif candidate.trigger_type is QuestionTriggerType.PENDING_PRIORITY_CONFIRMATION:
        valid_targets = {
            f"priority:{item.priority_id}"
            for item in context.pending_priority_confirmations
        }
        if candidate.target_input_id not in valid_targets:
            raise MaterialQuestionPlannerError(
                "priority-confirmation question must target a pending inferred priority"
            )


def plan_material_questions(
    *,
    plan_id: str,
    boundary: PersonalizationBoundaryDecision,
    context: CustomerDecisionContext,
    candidates: tuple[MaterialQuestionCandidate, ...],
    max_questions: int = 3,
) -> MaterialQuestionPlan:
    """Plan only explicitly nominated questions with traceable material triggers.

    The planner never sweeps all missing or inferred customer fields. Upstream
    governed reasoning must nominate a question because answering it can materially
    clarify an active comparison, applicability dependency, hard constraint, or
    inferred value that is actually needed for the current decision analysis.
    """

    if type(boundary) is not PersonalizationBoundaryDecision:
        raise MaterialQuestionPlannerError(
            "boundary must be the exact PersonalizationBoundaryDecision type"
        )
    if type(context) is not CustomerDecisionContext:
        raise MaterialQuestionPlannerError(
            "context must be the exact CustomerDecisionContext type"
        )
    if boundary.customer_context_access is not CustomerContextAccess.PERMITTED:
        raise MaterialQuestionPlannerError(
            "material customer questions require permitted personalized-context access"
        )
    if boundary.active_customer_context_id != context.context_id:
        raise MaterialQuestionPlannerError(
            "boundary customer context must match the question-planning context"
        )
    if not isinstance(candidates, tuple) or not all(
        type(item) is MaterialQuestionCandidate for item in candidates
    ):
        raise MaterialQuestionPlannerError(
            "candidates must contain exact MaterialQuestionCandidate values"
        )
    if not isinstance(max_questions, int) or isinstance(max_questions, bool) or max_questions < 1:
        raise MaterialQuestionPlannerError("max_questions must be a positive integer")

    for candidate in candidates:
        _validate_confirmation_candidate(candidate=candidate, context=context)

    ordered = sorted(
        candidates,
        key=lambda item: (_PRIORITY_ORDER[item.priority], item.question_id),
    )

    selected: list[MaterialQuestionCandidate] = []
    seen_targets: set[str] = set()
    for candidate in ordered:
        if candidate.target_input_id in seen_targets:
            continue
        selected.append(candidate)
        seen_targets.add(candidate.target_input_id)
        if len(selected) >= max_questions:
            break

    return MaterialQuestionPlan(
        plan_id=plan_id,
        customer_context_id=context.context_id,
        questions=tuple(selected),
    )


__all__ = [
    "MaterialQuestionCandidate",
    "MaterialQuestionPlan",
    "MaterialQuestionPlannerError",
    "MaterialQuestionPriority",
    "QuestionTriggerType",
    "plan_material_questions",
]
