from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import build_approved_response_packet, build_finding_disposition, build_output as build_decision_output
from insurance_intelligence.contracts.explanation import build_fidelity_check as build_expl_check, build_output as build_explanation_output, build_section
from insurance_intelligence.contracts.llm_rendering import build_candidate_section, build_input
from insurance_intelligence.llm.policy import build_renderer_policy
from insurance_intelligence.llm.provider import DeterministicFakeProvider
from insurance_intelligence.llm.service import HybridRenderingResult, render_with_fallback


def rendering_input(*, text="When the condition applies, the insured pays 10%.", limitations=("Condition applies.",)):
    packet = build_approved_response_packet(packet_id="p", approved_finding_ids=("f1",), approved_evidence_ids=("e1",), limitation_ids=("l1",), prohibited_operations=("RECOMMEND",))
    disposition = build_finding_disposition(finding_id="f1", disposition="APPROVED_WITH_LIMITATIONS", basis="supported", approved_evidence_ids=("e1",), limitation_ids=("l1",), confidence=.9)
    decision = build_decision_output(request_id="r1", decision_id="d1", decision="APPROVED_WITH_LIMITATIONS", finding_dispositions=(disposition,), response_packet=packet, limitations=limitations, confidence=.9)
    section = build_section(section_id="s1", section_type="MEANING", status="DRAFTED", text=text, approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l1",))
    check = build_expl_check(check_id="c1", check_type="NO_NEW_FACTS", status="PASSED", description="ok", section_ids=("s1",))
    explanation = build_explanation_output(request_id="r1", explanation_id="x1", audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="CLAUSE_MEANING", sections=(section,), fidelity_checks=(check,), fidelity_status="VERIFIED", limitations=limitations, explanation_status="DRAFTED_WITH_LIMITATIONS" if limitations else "DRAFTED", confidence=.9)
    return build_input(request_id="r1", decision_output=decision, deterministic_explanation=explanation, provider_name="fake", model_name="model")


def policy():
    return build_renderer_policy(provider_name="fake", allowed_models=("model",), default_model="model", maximum_temperature=.2, maximum_output_tokens=500)


def candidate(text="When the condition applies, you pay 10%."):
    return build_candidate_section(section_id="cs1", source_section_id="s1", section_type="MEANING", text=text, approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l1",))


def run(*, text=None, failure=None, raw_output=None, limitations=("Condition applies.",)):
    provider = DeterministicFakeProvider(provider_name="fake", sections=() if failure else (candidate(text or "When the condition applies, you pay 10%."),), failure=failure)
    return render_with_fallback(rendering_input(limitations=limitations), policy(), provider, raw_output=raw_output), provider


def test_success_returns_hybrid_result():
    result, _ = run()
    assert isinstance(result, HybridRenderingResult)


def test_success_releases_verified_candidate():
    result, _ = run()
    assert result.output.rendered_sections[0].text == "When the condition applies, you pay 10%."


def test_success_does_not_use_fallback():
    result, _ = run()
    assert result.used_fallback is False and result.output.fallback is None


def test_success_with_limitations_status():
    result, _ = run()
    assert result.output.rendering_status == "RENDERED_WITH_LIMITATIONS"


def test_success_without_limitations_status():
    result, _ = run(limitations=())
    assert result.output.rendering_status == "RENDERED"


def test_success_preserves_deterministic_confidence():
    result, _ = run()
    assert result.output.confidence == .9


def test_provider_invoked_exactly_once():
    _, provider = run()
    assert provider.call_count == 1


def test_timeout_selects_fallback():
    result, _ = run(failure="TIMEOUT")
    assert result.used_fallback and result.output.fallback.reason == "TIMEOUT"


def test_provider_error_selects_fallback():
    result, _ = run(failure="ERROR")
    assert result.output.fallback.reason == "PROVIDER_ERROR"


def test_invalid_provider_response_selects_fallback():
    result, _ = run(failure="INVALID_RESPONSE")
    assert result.output.rendering_status == "PROVIDER_FAILED"


def test_provider_failure_exposes_no_candidate_sections():
    result, _ = run(failure="ERROR")
    assert result.output.rendered_sections == ()


def test_invalid_json_selects_fallback():
    result, _ = run(raw_output="not-json")
    assert result.output.fallback.reason == "INVALID_STRUCTURE"


def test_invalid_structure_exposes_no_candidate_sections():
    result, _ = run(raw_output={"sections": []})
    assert result.output.rendered_sections == ()


def test_numeric_change_selects_fallback():
    result, _ = run(text="When the condition applies, you pay 20%.")
    assert result.output.fallback.reason == "NUMERIC_CHANGE"


def test_missing_condition_selects_fallback():
    result, _ = run(text="You pay 10%.")
    assert result.output.fallback.reason == "MISSING_CONDITION"


def test_recommendation_selects_fallback():
    result, _ = run(text="When the condition applies, you pay 10%. You should buy this plan.")
    assert result.output.fallback.reason == "UNSUPPORTED_CONTENT"


def test_guarantee_selects_fallback():
    result, _ = run(text="When the condition applies, you pay 10% and the claim will be paid.")
    assert result.used_fallback


def test_fidelity_failure_preserves_validation_result():
    result, _ = run(text="When the condition applies, you pay 20%.")
    assert result.fidelity_validation is not None and result.fidelity_validation.status == "FAILED"


def test_parse_failure_has_no_parsed_output():
    result, _ = run(raw_output="bad")
    assert result.parsed_output is None


def test_success_preserves_parsed_output():
    result, _ = run()
    assert result.parsed_output is not None


def test_trace_is_ordered_and_completed():
    result, _ = run()
    assert [e.sequence for e in result.output.rendering_trace] == list(range(1, len(result.output.rendering_trace)+1))
    assert result.output.rendering_trace[-1].event_type == "RENDERING_COMPLETED"


def test_fallback_trace_contains_fallback_selected():
    result, _ = run(failure="ERROR")
    assert "FALLBACK_SELECTED" in [e.event_type for e in result.output.rendering_trace]


def test_result_identity_is_deterministic():
    first, _ = run()
    second, _ = run()
    assert first.service_result_id == second.service_result_id


def test_result_is_frozen():
    result, _ = run()
    with pytest.raises(FrozenInstanceError):
        result.used_fallback = True


def test_rejects_non_rendering_input():
    with pytest.raises(TypeError):
        render_with_fallback(object(), policy(), DeterministicFakeProvider(provider_name="fake", sections=(candidate(),)))
