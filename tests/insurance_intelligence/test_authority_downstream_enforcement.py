from __future__ import annotations

import pytest

from insurance_intelligence.authority_enforced_decision_gate import AuthorityEnforcedDecisionGate
from insurance_intelligence.contracts.authority_enforcement import (
    AuthorityEnforcementContractError,
    build_input,
    build_result,
)
from insurance_intelligence.contracts.authority_intent_reconciliation import build_output as build_reconciliation
from insurance_intelligence.contracts.decision import DecisionGateInput


class SpyDecisionGate:
    def __init__(self) -> None:
        self.calls = 0

    def decide(self, data):
        self.calls += 1
        return object()


def decision_input(request_id: str = "req-1") -> DecisionGateInput:
    # Direct construction is intentional: wrapper tests exercise only authority
    # preflight/delegation, not the already-proven DecisionGateInput validator.
    return DecisionGateInput(
        contract_version="1.0",
        request_id=request_id,
        reasoning_plan=None,  # type: ignore[arg-type]
        evidence_resolution=None,  # type: ignore[arg-type]
        reasoning_output=None,  # type: ignore[arg-type]
        decision_context={},
        strict_mode="STRICT",
    )


def reconciliation(
    *,
    authority_class="ASSERTIVE",
    primary_intent="POLICY_FACT_LOOKUP",
    status="CONSISTENT_ASSERTIVE",
    guard="STANDARD_ASSERTION_GROUNDING",
    advisory=False,
    authority_clarify=False,
    reconciliation_clarify=False,
    intent_exit=False,
    assertion_permitted=True,
):
    return build_reconciliation(
        request_id="req-1",
        authority_class=authority_class,
        primary_intent=primary_intent,
        secondary_intents=(),
        reconciliation_status=status,
        minimum_guard=guard,
        advisory_safety_obligation=advisory,
        authority_clarification_required=authority_clarify,
        reconciliation_clarification_required=reconciliation_clarify,
        intent_exit_required=intent_exit,
        ordinary_assertion_path_permitted=assertion_permitted,
        recommendation_authorized=False,
        basis="test fixture",
    )


def enforce(rec, spy=None):
    gate = spy or SpyDecisionGate()
    result = AuthorityEnforcedDecisionGate(gate).decide(
        build_input(
            request_id="req-1",
            reconciliation=rec,
            decision_gate_input=decision_input(),
        )
    )
    return result, gate


def test_consistent_assertive_path_delegates_to_existing_decision_gate():
    result, spy = enforce(reconciliation())
    assert result.enforcement_outcome == "DELEGATED_TO_DECISION_GATE"
    assert result.decision_gate_called is True
    assert result.ordinary_assertion_path_permitted is True
    assert result.advisory_safety_obligation is False
    assert spy.calls == 1


def test_advisory_path_is_withheld_before_decision_gate():
    rec = reconciliation(
        authority_class="ADVISORY",
        primary_intent="RECOMMENDATION",
        status="CONSISTENT_ADVISORY",
        guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
        advisory=True,
        assertion_permitted=False,
    )
    result, spy = enforce(rec)
    assert result.enforcement_outcome == "ADVISORY_PATH_NOT_AUTHORIZED"
    assert result.decision_gate_called is False
    assert result.recommendation_authorized is False
    assert spy.calls == 0


def test_mixed_path_is_withheld_before_decision_gate():
    rec = reconciliation(
        authority_class="MIXED",
        primary_intent="PRODUCT_COMPARISON",
        status="AUTHORITY_STRICTER_THAN_INTENT",
        guard="SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED",
        advisory=True,
        assertion_permitted=False,
    )
    result, spy = enforce(rec)
    assert result.enforcement_outcome == "ADVISORY_PATH_NOT_AUTHORIZED"
    assert spy.calls == 0


def test_unresolved_authority_requires_clarification_and_never_calls_gate():
    rec = reconciliation(
        authority_class="UNRESOLVED",
        status="AUTHORITY_UNRESOLVED",
        guard="ADVISORY_HOLD_AND_CLARIFY_AUTHORITY",
        advisory=True,
        authority_clarify=True,
        assertion_permitted=False,
    )
    result, spy = enforce(rec)
    assert result.enforcement_outcome == "AUTHORITY_CLARIFICATION_REQUIRED"
    assert result.clarification_required is True
    assert result.advisory_safety_obligation is True
    assert spy.calls == 0


def test_assertive_authority_advisory_intent_conflict_requires_reconciliation_clarification():
    rec = reconciliation(
        authority_class="ASSERTIVE",
        primary_intent="RECOMMENDATION",
        status="INTENT_RAISES_TO_ADVISORY",
        guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
        advisory=True,
        reconciliation_clarify=True,
        assertion_permitted=False,
    )
    result, spy = enforce(rec)
    assert result.enforcement_outcome == "RECONCILIATION_CLARIFICATION_REQUIRED"
    assert result.clarification_required is True
    assert spy.calls == 0


def test_intent_exit_is_preserved_before_decision_gate():
    rec = reconciliation(
        status="INTENT_EXIT_REQUIRED",
        guard="INTENT_EXIT_BEFORE_REASONING",
        intent_exit=True,
        assertion_permitted=False,
    )
    result, spy = enforce(rec)
    assert result.enforcement_outcome == "INTENT_EXIT_REQUIRED"
    assert result.clarification_required is True
    assert spy.calls == 0


def test_out_of_scope_is_preserved_before_decision_gate():
    rec = reconciliation(
        primary_intent="OUT_OF_SCOPE",
        status="OUT_OF_SCOPE",
        guard="OUT_OF_SCOPE_EXIT",
        intent_exit=True,
        assertion_permitted=False,
    )
    result, spy = enforce(rec)
    assert result.enforcement_outcome == "OUT_OF_SCOPE"
    assert result.out_of_scope is True
    assert spy.calls == 0


def test_cross_request_mismatch_is_rejected():
    with pytest.raises(AuthorityEnforcementContractError):
        build_input(
            request_id="req-1",
            reconciliation=reconciliation(),
            decision_gate_input=decision_input("other"),
        )


def test_enforcement_contract_never_authorizes_recommendation():
    with pytest.raises(AuthorityEnforcementContractError):
        build_result(
            request_id="req-1",
            enforcement_outcome="ADVISORY_PATH_NOT_AUTHORIZED",
            minimum_guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            advisory_safety_obligation=True,
            ordinary_assertion_path_permitted=False,
            decision_gate_called=False,
            decision_output=None,
            clarification_required=False,
            out_of_scope=False,
            basis="test",
            enforcement_trace=("test",),
            recommendation_authorized=True,
        )


def test_delegation_cannot_be_forged_for_advisory_posture():
    with pytest.raises(AuthorityEnforcementContractError):
        build_result(
            request_id="req-1",
            enforcement_outcome="DELEGATED_TO_DECISION_GATE",
            minimum_guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            advisory_safety_obligation=True,
            ordinary_assertion_path_permitted=False,
            decision_gate_called=True,
            decision_output=object(),  # type: ignore[arg-type]
            clarification_required=False,
            out_of_scope=False,
            basis="test",
            enforcement_trace=("test",),
        )


def test_nonassertive_preflight_never_invokes_legacy_gate():
    scenarios = (
        reconciliation(
            authority_class="ADVISORY", primary_intent="RECOMMENDATION",
            status="CONSISTENT_ADVISORY", guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            advisory=True, assertion_permitted=False,
        ),
        reconciliation(
            authority_class="MIXED", status="AUTHORITY_STRICTER_THAN_INTENT",
            guard="SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED",
            advisory=True, assertion_permitted=False,
        ),
        reconciliation(
            authority_class="UNRESOLVED", status="AUTHORITY_UNRESOLVED",
            guard="ADVISORY_HOLD_AND_CLARIFY_AUTHORITY", advisory=True,
            authority_clarify=True, assertion_permitted=False,
        ),
    )
    spy = SpyDecisionGate()
    wrapper = AuthorityEnforcedDecisionGate(spy)
    for rec in scenarios:
        wrapper.decide(build_input(request_id="req-1", reconciliation=rec, decision_gate_input=decision_input()))
    assert spy.calls == 0
