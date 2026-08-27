from __future__ import annotations

import pytest

from insurance_intelligence.authority_enforced_explanation import (
    AuthorityEnforcedExplanationGenerator,
    AuthorityExplanationEnforcementError,
)
from insurance_intelligence.contracts.authority_enforcement import build_result
from insurance_intelligence.contracts.decision import (
    DecisionGateOutput,
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)


def approved_decision() -> DecisionGateOutput:
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED_WITH_LIMITATIONS",
        basis="Supported with limitation.",
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        confidence=0.9,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED_WITH_LIMITATIONS",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=("Condition remains explicit.",),
        confidence=0.9,
    )


def delegated_result():
    return build_result(
        request_id="request-1",
        enforcement_outcome="DELEGATED_TO_DECISION_GATE",
        minimum_guard="STANDARD_ASSERTION_GROUNDING",
        advisory_safety_obligation=False,
        ordinary_assertion_path_permitted=True,
        decision_gate_called=True,
        decision_output=approved_decision(),
        clarification_required=False,
        out_of_scope=False,
        basis="ordinary assertive path cleared",
        enforcement_trace=("delegated",),
    )


def blocked_result(outcome="ADVISORY_PATH_NOT_AUTHORIZED", *, advisory=True, clarification=False, out_of_scope=False):
    return build_result(
        request_id="request-1",
        enforcement_outcome=outcome,
        minimum_guard=(
            "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED"
            if advisory
            else ("OUT_OF_SCOPE_EXIT" if out_of_scope else "INTENT_EXIT_BEFORE_REASONING")
        ),
        advisory_safety_obligation=advisory,
        ordinary_assertion_path_permitted=False,
        decision_gate_called=False,
        decision_output=None,
        clarification_required=clarification,
        out_of_scope=out_of_scope,
        basis="blocked before decision gate",
        enforcement_trace=("blocked",),
    )


class SpyGenerator:
    def __init__(self):
        self.calls = 0
        self.last_input = None

    def __call__(self, **kwargs):
        self.calls += 1
        self.last_input = kwargs["explanation_input"]
        return "generated"


def test_delegated_assertive_result_may_enter_existing_explanation_generator():
    spy = SpyGenerator()
    output = AuthorityEnforcedExplanationGenerator(spy).generate(
        authority_result=delegated_result(),
        findings_by_id={},
        style_registry=object(),  # type: ignore[arg-type]
    )
    assert output == "generated"
    assert spy.calls == 1
    assert spy.last_input.request_id == "request-1"
    assert spy.last_input.decision_output.decision_id == "decision-1"


def test_advisory_path_cannot_render_and_generator_is_not_called():
    spy = SpyGenerator()
    with pytest.raises(AuthorityExplanationEnforcementError):
        AuthorityEnforcedExplanationGenerator(spy).generate(
            authority_result=blocked_result(), findings_by_id={}, style_registry=object()  # type: ignore[arg-type]
        )
    assert spy.calls == 0


def test_unresolved_authority_clarification_cannot_render_through_ordinary_path():
    spy = SpyGenerator()
    result = blocked_result(
        "AUTHORITY_CLARIFICATION_REQUIRED", advisory=True, clarification=True
    )
    with pytest.raises(AuthorityExplanationEnforcementError):
        AuthorityEnforcedExplanationGenerator(spy).generate(
            authority_result=result, findings_by_id={}, style_registry=object()  # type: ignore[arg-type]
        )
    assert spy.calls == 0


def test_reconciliation_conflict_cannot_render():
    result = blocked_result(
        "RECONCILIATION_CLARIFICATION_REQUIRED", advisory=True, clarification=True
    )
    with pytest.raises(AuthorityExplanationEnforcementError):
        AuthorityEnforcedExplanationGenerator(SpyGenerator()).generate(
            authority_result=result, findings_by_id={}, style_registry=object()  # type: ignore[arg-type]
        )


def test_intent_exit_cannot_render():
    result = blocked_result("INTENT_EXIT_REQUIRED", advisory=False, clarification=True)
    with pytest.raises(AuthorityExplanationEnforcementError):
        AuthorityEnforcedExplanationGenerator(SpyGenerator()).generate(
            authority_result=result, findings_by_id={}, style_registry=object()  # type: ignore[arg-type]
        )


def test_out_of_scope_cannot_render():
    result = blocked_result("OUT_OF_SCOPE", advisory=False, out_of_scope=True)
    with pytest.raises(AuthorityExplanationEnforcementError):
        AuthorityEnforcedExplanationGenerator(SpyGenerator()).generate(
            authority_result=result, findings_by_id={}, style_registry=object()  # type: ignore[arg-type]
        )


def test_raw_decision_output_is_not_accepted_as_authority_result():
    with pytest.raises(AuthorityExplanationEnforcementError):
        AuthorityEnforcedExplanationGenerator(SpyGenerator()).generate(
            authority_result=approved_decision(),  # type: ignore[arg-type]
            findings_by_id={},
            style_registry=object(),  # type: ignore[arg-type]
        )
