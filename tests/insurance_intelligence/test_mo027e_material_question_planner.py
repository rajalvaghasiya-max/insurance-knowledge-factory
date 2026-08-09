import pytest

from insurance_intelligence.decision_support.customer_context import (
    CustomerContextProvenance,
    CustomerDecisionContext,
    CustomerPriority,
    PriorityImportance,
)
from insurance_intelligence.decision_support.material_question_planner import (
    MaterialQuestionCandidate,
    MaterialQuestionPlannerError,
    MaterialQuestionPriority,
    QuestionTriggerType,
    plan_material_questions,
)
from insurance_intelligence.decision_support.personalization_boundary import (
    PersonalizationBoundaryState,
    PersonalizationState,
    TurnIntent,
    decide_personalization_boundary,
)


CONTEXT_ID = "customer_context:mother:v1"


def context(*, inferred_priority: bool = False) -> CustomerDecisionContext:
    priorities = ()
    if inferred_priority:
        priorities = (
            CustomerPriority(
                priority_id="priority:claim_time_oop",
                dimension_id="copayment",
                importance=PriorityImportance.HIGH,
                provenance=CustomerContextProvenance.INFERRED,
                raw_statement="I don't want surprises during claims.",
            ),
        )
    return CustomerDecisionContext(
        context_id=CONTEXT_ID,
        subject_references=("customer_subject:mother",),
        priorities=priorities,
    )


def personalized_boundary():
    prior = PersonalizationBoundaryState(
        state_id="state:product-only",
        state=PersonalizationState.PRODUCT_ONLY,
    )
    return decide_personalization_boundary(
        decision_id="boundary:enter",
        prior=prior,
        intent=TurnIntent.PERSONALIZED_DECISION_SUPPORT,
        customer_context_id=CONTEXT_ID,
    )


def candidate(
    *,
    question_id: str,
    trigger_type: QuestionTriggerType,
    target_input_id: str,
    dimension_id: str = "copayment",
    priority: MaterialQuestionPriority = MaterialQuestionPriority.HIGH,
) -> MaterialQuestionCandidate:
    return MaterialQuestionCandidate(
        question_id=question_id,
        trigger_type=trigger_type,
        prompt="Please clarify this decision-relevant point.",
        target_input_id=target_input_id,
        material_dimension_ids=(dimension_id,),
        trigger_reference_ids=("tradeoff:star-vs-activ-one:v1",),
        priority=priority,
        why_material="The answer can materially clarify an active product trade-off.",
    )


def test_planner_requires_personalized_context_access() -> None:
    prior = PersonalizationBoundaryState(
        state_id="state:product-only",
        state=PersonalizationState.PRODUCT_ONLY,
    )
    boundary = decide_personalization_boundary(
        decision_id="boundary:product-only",
        prior=prior,
        intent=TurnIntent.PRODUCT_ONLY,
    )
    with pytest.raises(MaterialQuestionPlannerError, match="permitted personalized-context"):
        plan_material_questions(
            plan_id="plan:invalid",
            boundary=boundary,
            context=context(),
            candidates=(),
        )


def test_planner_does_not_auto_ask_about_untriggered_inferred_priority() -> None:
    result = plan_material_questions(
        plan_id="plan:no-sweep",
        boundary=personalized_boundary(),
        context=context(inferred_priority=True),
        candidates=(),
    )
    assert result.questions == ()
    assert result.has_questions is False


def test_material_inferred_priority_can_be_nominated_for_confirmation() -> None:
    item = candidate(
        question_id="question:confirm-copay-priority",
        trigger_type=QuestionTriggerType.PENDING_PRIORITY_CONFIRMATION,
        target_input_id="priority:priority:claim_time_oop",
    )
    result = plan_material_questions(
        plan_id="plan:confirm-priority",
        boundary=personalized_boundary(),
        context=context(inferred_priority=True),
        candidates=(item,),
    )
    assert result.questions == (item,)


def test_confirmation_question_must_target_pending_inferred_value() -> None:
    item = candidate(
        question_id="question:invalid-confirm",
        trigger_type=QuestionTriggerType.PENDING_PRIORITY_CONFIRMATION,
        target_input_id="priority:not-pending",
    )
    with pytest.raises(MaterialQuestionPlannerError, match="pending inferred priority"):
        plan_material_questions(
            plan_id="plan:invalid-confirm",
            boundary=personalized_boundary(),
            context=context(inferred_priority=True),
            candidates=(item,),
        )


def test_unresolved_dimension_question_requires_traceable_trigger() -> None:
    with pytest.raises(MaterialQuestionPlannerError, match="trigger_reference_ids"):
        MaterialQuestionCandidate(
            question_id="question:room-rent",
            trigger_type=QuestionTriggerType.UNRESOLVED_COMPARISON_DIMENSION,
            prompt="Can you share the missing room-rent detail?",
            target_input_id="room_rent:missing_detail",
            material_dimension_ids=("room_rent_restriction",),
            trigger_reference_ids=(),
            priority=MaterialQuestionPriority.HIGH,
            why_material="The room-rent comparison is unresolved.",
        )


def test_planner_orders_critical_before_high_before_normal() -> None:
    normal = candidate(
        question_id="question:z-normal",
        trigger_type=QuestionTriggerType.UNRESOLVED_COMPARISON_DIMENSION,
        target_input_id="input:normal",
        priority=MaterialQuestionPriority.NORMAL,
    )
    critical = candidate(
        question_id="question:z-critical",
        trigger_type=QuestionTriggerType.DECLARED_HARD_CONSTRAINT_CLARIFICATION,
        target_input_id="input:critical",
        priority=MaterialQuestionPriority.CRITICAL,
    )
    high = candidate(
        question_id="question:z-high",
        trigger_type=QuestionTriggerType.GOVERNED_APPLICABILITY_DEPENDENCY,
        target_input_id="input:high",
        priority=MaterialQuestionPriority.HIGH,
    )
    result = plan_material_questions(
        plan_id="plan:ordered",
        boundary=personalized_boundary(),
        context=context(),
        candidates=(normal, high, critical),
    )
    assert [item.question_id for item in result.questions] == [
        "question:z-critical",
        "question:z-high",
        "question:z-normal",
    ]


def test_planner_limits_questions_and_deduplicates_same_target() -> None:
    first = candidate(
        question_id="question:a",
        trigger_type=QuestionTriggerType.UNRESOLVED_COMPARISON_DIMENSION,
        target_input_id="input:one",
        priority=MaterialQuestionPriority.CRITICAL,
    )
    duplicate_target = candidate(
        question_id="question:b",
        trigger_type=QuestionTriggerType.GOVERNED_APPLICABILITY_DEPENDENCY,
        target_input_id="input:one",
        priority=MaterialQuestionPriority.HIGH,
    )
    second = candidate(
        question_id="question:c",
        trigger_type=QuestionTriggerType.UNRESOLVED_COMPARISON_DIMENSION,
        target_input_id="input:two",
        priority=MaterialQuestionPriority.HIGH,
    )
    third = candidate(
        question_id="question:d",
        trigger_type=QuestionTriggerType.UNRESOLVED_COMPARISON_DIMENSION,
        target_input_id="input:three",
        priority=MaterialQuestionPriority.NORMAL,
    )
    result = plan_material_questions(
        plan_id="plan:bounded",
        boundary=personalized_boundary(),
        context=context(),
        candidates=(third, duplicate_target, second, first),
        max_questions=2,
    )
    assert [item.target_input_id for item in result.questions] == ["input:one", "input:two"]


def test_question_contract_has_no_weight_lean_or_recommendation_fields() -> None:
    forbidden = {
        "weight",
        "score",
        "overall_score",
        "lean",
        "winner",
        "recommendation",
        "suitability",
        "should_prioritize",
    }
    assert forbidden.isdisjoint(MaterialQuestionCandidate.__dataclass_fields__)
