import pytest

from insurance_intelligence.decision_support.personalization_boundary import (
    ContextTransition,
    CustomerContextAccess,
    PersonalizationBoundaryError,
    PersonalizationBoundaryState,
    PersonalizationState,
    TurnIntent,
    decide_personalization_boundary,
    next_boundary_state,
)


def product_state() -> PersonalizationBoundaryState:
    return PersonalizationBoundaryState(
        state_id="state:product-only",
        state=PersonalizationState.PRODUCT_ONLY,
    )


def personalized_state() -> PersonalizationBoundaryState:
    return PersonalizationBoundaryState(
        state_id="state:personalized",
        state=PersonalizationState.PERSONALIZED_ACTIVE,
        active_customer_context_id="customer_context:mother:v1",
    )


def test_product_only_turn_never_gets_customer_context_access() -> None:
    result = decide_personalization_boundary(
        decision_id="decision:product-only:v1",
        prior=product_state(),
        intent=TurnIntent.PRODUCT_ONLY,
    )
    assert result.transition is ContextTransition.STAY_PRODUCT_ONLY
    assert result.next_state is PersonalizationState.PRODUCT_ONLY
    assert result.customer_context_access is CustomerContextAccess.PROHIBITED
    assert result.active_customer_context_id is None


def test_entering_personalized_context_requires_explicit_context_binding() -> None:
    with pytest.raises(PersonalizationBoundaryError, match="customer_context_id"):
        decide_personalization_boundary(
            decision_id="decision:enter:v1",
            prior=product_state(),
            intent=TurnIntent.PERSONALIZED_DECISION_SUPPORT,
        )

    result = decide_personalization_boundary(
        decision_id="decision:enter:v2",
        prior=product_state(),
        intent=TurnIntent.PERSONALIZED_DECISION_SUPPORT,
        customer_context_id="customer_context:mother:v1",
    )
    assert result.transition is ContextTransition.ENTER_PERSONALIZED
    assert result.customer_context_access is CustomerContextAccess.PERMITTED
    assert result.active_customer_context_id == "customer_context:mother:v1"


def test_personalized_implication_intent_also_requires_personalized_boundary() -> None:
    result = decide_personalization_boundary(
        decision_id="decision:implication:v1",
        prior=product_state(),
        intent=TurnIntent.PERSONALIZED_IMPLICATION,
        customer_context_id="customer_context:self:v1",
    )
    assert result.transition is ContextTransition.ENTER_PERSONALIZED
    assert result.next_state is PersonalizationState.PERSONALIZED_ACTIVE


def test_personalized_turn_continues_only_same_customer_context() -> None:
    result = decide_personalization_boundary(
        decision_id="decision:continue:v1",
        prior=personalized_state(),
        intent=TurnIntent.PERSONALIZED_DECISION_SUPPORT,
    )
    assert result.transition is ContextTransition.CONTINUE_PERSONALIZED
    assert result.active_customer_context_id == "customer_context:mother:v1"

    with pytest.raises(PersonalizationBoundaryError, match="cannot silently replace"):
        decide_personalization_boundary(
            decision_id="decision:switch:v1",
            prior=personalized_state(),
            intent=TurnIntent.PERSONALIZED_DECISION_SUPPORT,
            customer_context_id="customer_context:father:v1",
        )


def test_backward_drift_to_product_only_drops_personal_context_access() -> None:
    result = decide_personalization_boundary(
        decision_id="decision:exit:v1",
        prior=personalized_state(),
        intent=TurnIntent.PRODUCT_ONLY,
    )
    assert result.transition is ContextTransition.EXIT_TO_PRODUCT_ONLY
    assert result.next_state is PersonalizationState.PRODUCT_ONLY
    assert result.customer_context_access is CustomerContextAccess.PROHIBITED
    assert result.active_customer_context_id is None


def test_next_state_cannot_retain_context_after_product_only_exit() -> None:
    decision = decide_personalization_boundary(
        decision_id="decision:exit:v2",
        prior=personalized_state(),
        intent=TurnIntent.PRODUCT_ONLY,
    )
    state = next_boundary_state(decision)
    assert state.state is PersonalizationState.PRODUCT_ONLY
    assert state.active_customer_context_id is None


def test_product_only_state_rejects_embedded_customer_context() -> None:
    with pytest.raises(PersonalizationBoundaryError, match="cannot carry"):
        PersonalizationBoundaryState(
            state_id="invalid:product-with-context",
            state=PersonalizationState.PRODUCT_ONLY,
            active_customer_context_id="customer_context:mother:v1",
        )


def test_boundary_contract_contains_no_recommendation_or_net_direction() -> None:
    from insurance_intelligence.decision_support.personalization_boundary import (
        PersonalizationBoundaryDecision,
    )

    forbidden = {
        "winner",
        "recommendation",
        "suitability",
        "net_direction",
        "lean",
        "score",
        "weight",
    }
    assert forbidden.isdisjoint(PersonalizationBoundaryDecision.__dataclass_fields__)
