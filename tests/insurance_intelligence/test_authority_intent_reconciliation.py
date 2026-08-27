from __future__ import annotations

import pytest

from insurance_intelligence.authority_intent_reconciliation import (
    reconcile_authority_and_intent,
)
from insurance_intelligence.contracts.authority_intent_reconciliation import (
    AuthorityIntentReconciliationError,
    build_input as build_reconciliation_input,
    build_output as build_reconciliation_output,
)
from insurance_intelligence.contracts.intent import build_output as build_intent_output
from insurance_intelligence.contracts.request_authority import build_input as build_authority_input
from insurance_intelligence.request_authority import classify_request_authority


def intent(
    request_id: str,
    primary: str,
    *,
    secondary: tuple[str, ...] = (),
    status: str = "CLASSIFIED",
):
    return build_intent_output(
        request_id=request_id,
        primary_intent=primary,
        secondary_intents=secondary,
        domain="health" if primary != "OUT_OF_SCOPE" else "unknown",
        requested_outcome="test",
        confidence=0.9,
        analysis_status=status,
        classification_basis=("question_pattern",),
        clarification_question=("Please clarify the request." if status == "CLARIFICATION_REQUIRED" else None),
    )


def authority(request_id: str, text: str):
    return classify_request_authority(build_authority_input(request_id=request_id, text=text))


def reconcile(request_id: str, text: str, primary: str, **kwargs):
    return reconcile_authority_and_intent(
        build_reconciliation_input(
            request_id=request_id,
            authority=authority(request_id, text),
            intent=intent(request_id, primary, **kwargs),
        )
    )


def test_consistent_assertive_request_permits_only_standard_assertion_path() -> None:
    result = reconcile("r1", "What is a co-pay?", "TERM_EXPLANATION")
    assert result.reconciliation_status == "CONSISTENT_ASSERTIVE"
    assert result.minimum_guard == "STANDARD_ASSERTION_GROUNDING"
    assert result.ordinary_assertion_path_permitted is True
    assert result.advisory_safety_obligation is False
    assert result.recommendation_authorized is False


@pytest.mark.parametrize("primary", ["RECOMMENDATION", "SUITABILITY_ASSESSMENT"])
def test_assertive_authority_is_raised_when_intent_signals_advice(primary: str) -> None:
    result = reconcile("r2", "Explain this option.", primary)
    assert result.reconciliation_status == "INTENT_RAISES_TO_ADVISORY"
    assert result.minimum_guard == "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED"
    assert result.advisory_safety_obligation is True
    assert result.reconciliation_clarification_required is True
    assert result.ordinary_assertion_path_permitted is False


def test_secondary_recommendation_intent_also_raises_assertive_authority() -> None:
    result = reconcile(
        "r3",
        "Compare these two policies.",
        "POLICY_COMPARISON",
        secondary=("RECOMMENDATION",),
    )
    assert result.reconciliation_status == "INTENT_RAISES_TO_ADVISORY"
    assert result.advisory_safety_obligation is True


def test_advisory_authority_cannot_be_weakened_by_factual_intent() -> None:
    result = reconcile("r4", "Should I choose this policy?", "PRODUCT_EXPLANATION")
    assert result.reconciliation_status == "AUTHORITY_STRICTER_THAN_INTENT"
    assert result.minimum_guard == "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED"
    assert result.advisory_safety_obligation is True
    assert result.ordinary_assertion_path_permitted is False


def test_advisory_authority_and_recommendation_intent_are_consistent() -> None:
    result = reconcile("r5", "Which policy should I buy?", "RECOMMENDATION")
    assert result.reconciliation_status == "CONSISTENT_ADVISORY"
    assert result.advisory_safety_obligation is True
    assert result.recommendation_authorized is False


def test_mixed_authority_preserves_split_guard_even_with_plain_comparison_intent() -> None:
    result = reconcile(
        "r6",
        "Compare these policies and tell me which is better for me.",
        "POLICY_COMPARISON",
    )
    assert result.reconciliation_status == "AUTHORITY_STRICTER_THAN_INTENT"
    assert result.minimum_guard == "SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED"
    assert result.advisory_safety_obligation is True


def test_mixed_authority_and_secondary_recommendation_are_consistent() -> None:
    result = reconcile(
        "r7",
        "Compare these policies and tell me which is better for me.",
        "POLICY_COMPARISON",
        secondary=("RECOMMENDATION",),
    )
    assert result.reconciliation_status == "CONSISTENT_MIXED"
    assert result.minimum_guard == "SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED"


def test_unresolved_authority_holds_stricter_guard_even_when_intent_resolves() -> None:
    result = reconcile("r8", "And this one?", "POLICY_FACT_LOOKUP")
    assert result.reconciliation_status == "AUTHORITY_UNRESOLVED"
    assert result.minimum_guard == "ADVISORY_HOLD_AND_CLARIFY_AUTHORITY"
    assert result.authority_clarification_required is True
    assert result.advisory_safety_obligation is True
    assert result.ordinary_assertion_path_permitted is False


def test_intent_clarification_exit_happens_before_reasoning() -> None:
    result = reconcile(
        "r9",
        "What is this?",
        "FOLLOW_UP",
        status="CLARIFICATION_REQUIRED",
    )
    assert result.reconciliation_status == "INTENT_EXIT_REQUIRED"
    assert result.minimum_guard == "INTENT_EXIT_BEFORE_REASONING"
    assert result.intent_exit_required is True
    assert result.ordinary_assertion_path_permitted is False


def test_out_of_scope_intent_exits_without_erasing_authority_metadata() -> None:
    result = reconcile("r10", "What is the weather?", "OUT_OF_SCOPE", status="OUT_OF_SCOPE")
    assert result.reconciliation_status == "OUT_OF_SCOPE"
    assert result.minimum_guard == "OUT_OF_SCOPE_EXIT"
    assert result.intent_exit_required is True
    assert result.recommendation_authorized is False


def test_reconciliation_requires_matching_request_ids() -> None:
    with pytest.raises(AuthorityIntentReconciliationError):
        build_reconciliation_input(
            request_id="r11",
            authority=authority("r11", "What is a co-pay?"),
            intent=intent("different", "TERM_EXPLANATION"),
        )


def test_contract_never_allows_recommendation_authorization() -> None:
    with pytest.raises(AuthorityIntentReconciliationError):
        build_reconciliation_output(
            request_id="r12",
            authority_class="ADVISORY",
            primary_intent="RECOMMENDATION",
            secondary_intents=(),
            reconciliation_status="CONSISTENT_ADVISORY",
            minimum_guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            advisory_safety_obligation=True,
            authority_clarification_required=False,
            reconciliation_clarification_required=False,
            intent_exit_required=False,
            ordinary_assertion_path_permitted=False,
            recommendation_authorized=True,
            basis="test",
        )


def test_contract_rejects_assertion_path_when_advisory_obligation_exists() -> None:
    with pytest.raises(AuthorityIntentReconciliationError):
        build_reconciliation_output(
            request_id="r13",
            authority_class="ADVISORY",
            primary_intent="PRODUCT_EXPLANATION",
            secondary_intents=(),
            reconciliation_status="AUTHORITY_STRICTER_THAN_INTENT",
            minimum_guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            advisory_safety_obligation=True,
            authority_clarification_required=False,
            reconciliation_clarification_required=False,
            intent_exit_required=False,
            ordinary_assertion_path_permitted=True,
            basis="test",
        )
