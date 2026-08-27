"""Deterministic reconciliation of independent authority and intent outputs."""
from __future__ import annotations

from insurance_intelligence.contracts.authority_intent_reconciliation import (
    AuthorityIntentReconciliationInput,
    AuthorityIntentReconciliationOutput,
    build_output,
)

ADVISORY_INTENTS = frozenset({"RECOMMENDATION", "SUITABILITY_ASSESSMENT"})
INTENT_EXIT_STATUSES = frozenset({"CLARIFICATION_REQUIRED", "INVALID_REQUEST"})


def reconcile_authority_and_intent(
    request: AuthorityIntentReconciliationInput,
) -> AuthorityIntentReconciliationOutput:
    authority = request.authority
    intent = request.intent
    intent_labels = frozenset({intent.primary_intent, *intent.secondary_intents})
    intent_signals_advisory = bool(intent_labels & ADVISORY_INTENTS)

    if intent.analysis_status == "OUT_OF_SCOPE" or intent.primary_intent == "OUT_OF_SCOPE":
        return build_output(
            request_id=request.request_id,
            authority_class=authority.authority_class,
            primary_intent=intent.primary_intent,
            secondary_intents=intent.secondary_intents,
            reconciliation_status="OUT_OF_SCOPE",
            minimum_guard="OUT_OF_SCOPE_EXIT",
            advisory_safety_obligation=authority.advisory_safety_obligation,
            authority_clarification_required=authority.authority_clarification_required,
            reconciliation_clarification_required=False,
            intent_exit_required=True,
            ordinary_assertion_path_permitted=False,
            basis="intent_out_of_scope_exit_preserves_authority_metadata",
        )

    if intent.analysis_status in INTENT_EXIT_STATUSES:
        return build_output(
            request_id=request.request_id,
            authority_class=authority.authority_class,
            primary_intent=intent.primary_intent,
            secondary_intents=intent.secondary_intents,
            reconciliation_status="INTENT_EXIT_REQUIRED",
            minimum_guard="INTENT_EXIT_BEFORE_REASONING",
            advisory_safety_obligation=(
                authority.advisory_safety_obligation or intent_signals_advisory
            ),
            authority_clarification_required=authority.authority_clarification_required,
            reconciliation_clarification_required=False,
            intent_exit_required=True,
            ordinary_assertion_path_permitted=False,
            basis="intent_analysis_requires_exit_before_reasoning",
        )

    if authority.authority_class == "UNRESOLVED":
        return build_output(
            request_id=request.request_id,
            authority_class=authority.authority_class,
            primary_intent=intent.primary_intent,
            secondary_intents=intent.secondary_intents,
            reconciliation_status="AUTHORITY_UNRESOLVED",
            minimum_guard="ADVISORY_HOLD_AND_CLARIFY_AUTHORITY",
            advisory_safety_obligation=True,
            authority_clarification_required=True,
            reconciliation_clarification_required=False,
            intent_exit_required=False,
            ordinary_assertion_path_permitted=False,
            basis="unresolved_authority_retains_stricter_advisory_hold",
        )

    if authority.authority_class == "ASSERTIVE" and intent_signals_advisory:
        return build_output(
            request_id=request.request_id,
            authority_class=authority.authority_class,
            primary_intent=intent.primary_intent,
            secondary_intents=intent.secondary_intents,
            reconciliation_status="INTENT_RAISES_TO_ADVISORY",
            minimum_guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            advisory_safety_obligation=True,
            authority_clarification_required=False,
            reconciliation_clarification_required=True,
            intent_exit_required=False,
            ordinary_assertion_path_permitted=False,
            basis="advisory_intent_signal_may_raise_but_never_lower_authority_guard",
        )

    if authority.authority_class == "MIXED":
        return build_output(
            request_id=request.request_id,
            authority_class=authority.authority_class,
            primary_intent=intent.primary_intent,
            secondary_intents=intent.secondary_intents,
            reconciliation_status=(
                "CONSISTENT_MIXED" if intent_signals_advisory else "AUTHORITY_STRICTER_THAN_INTENT"
            ),
            minimum_guard="SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED",
            advisory_safety_obligation=True,
            authority_clarification_required=False,
            reconciliation_clarification_required=False,
            intent_exit_required=False,
            ordinary_assertion_path_permitted=False,
            basis="mixed_authority_is_monotonic_and_cannot_be_weakened_by_intent",
        )

    if authority.authority_class == "ADVISORY":
        return build_output(
            request_id=request.request_id,
            authority_class=authority.authority_class,
            primary_intent=intent.primary_intent,
            secondary_intents=intent.secondary_intents,
            reconciliation_status=(
                "CONSISTENT_ADVISORY" if intent_signals_advisory else "AUTHORITY_STRICTER_THAN_INTENT"
            ),
            minimum_guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            advisory_safety_obligation=True,
            authority_clarification_required=False,
            reconciliation_clarification_required=False,
            intent_exit_required=False,
            ordinary_assertion_path_permitted=False,
            basis="advisory_authority_cannot_be_weakened_by_non_advisory_intent",
        )

    return build_output(
        request_id=request.request_id,
        authority_class=authority.authority_class,
        primary_intent=intent.primary_intent,
        secondary_intents=intent.secondary_intents,
        reconciliation_status="CONSISTENT_ASSERTIVE",
        minimum_guard="STANDARD_ASSERTION_GROUNDING",
        advisory_safety_obligation=False,
        authority_clarification_required=False,
        reconciliation_clarification_required=False,
        intent_exit_required=False,
        ordinary_assertion_path_permitted=True,
        basis="assertive_authority_and_non_advisory_intent_are_consistent",
    )
