from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import build_approved_response_packet, build_finding_disposition, build_output as build_decision_output
from insurance_intelligence.contracts.explanation import build_fidelity_check as build_expl_check, build_output as build_explanation_output, build_section
from insurance_intelligence.contracts.llm_rendering import build_candidate_section, build_input
from insurance_intelligence.evaluation.llm_baseline import (
    LLMBaselineError,
    HybridBaselineReport,
    build_case,
    evaluate_case,
    evaluate_hybrid_baseline,
    readability_signals,
)
from insurance_intelligence.llm.policy import build_renderer_policy
from insurance_intelligence.llm.provider import DeterministicFakeProvider
from insurance_intelligence.llm.service import render_with_fallback


def rendering_input(text="When the condition is applicable, the insured shall bear 10% of the admissible claim amount."):
    packet = build_approved_response_packet(packet_id="p", approved_finding_ids=("f1",), approved_evidence_ids=("e1",), limitation_ids=("l1",), prohibited_operations=("RECOMMEND",))
    disposition = build_finding_disposition(finding_id="f1", disposition="APPROVED_WITH_LIMITATIONS", basis="supported", approved_evidence_ids=("e1",), limitation_ids=("l1",), confidence=.9)
    decision = build_decision_output(request_id="r1", decision_id="d1", decision="APPROVED_WITH_LIMITATIONS", finding_dispositions=(disposition,), response_packet=packet, limitations=("Condition applies.",), confidence=.9)
    section = build_section(section_id="s1", section_type="MEANING", status="DRAFTED", text=text, approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l1",))
    check = build_expl_check(check_id="c1", check_type="NO_NEW_FACTS", status="PASSED", description="ok", section_ids=("s1",))
    explanation = build_explanation_output(request_id="r1", explanation_id="x1", audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="CLAUSE_MEANING", sections=(section,), fidelity_checks=(check,), fidelity_status="VERIFIED", limitations=("Condition applies.",), explanation_status="DRAFTED_WITH_LIMITATIONS", confidence=.9)
    return build_input(request_id="r1", decision_output=decision, deterministic_explanation=explanation, provider_name="fake", model_name="model")


def policy():
    return build_renderer_policy(provider_name="fake", allowed_models=("model",), default_model="model", maximum_temperature=.2, maximum_output_tokens=500)


def result(*, text="When the condition applies, you pay 10% of the claim amount.", failure=None):
    candidate = build_candidate_section(section_id="cs1", source_section_id="s1", section_type="MEANING", text=text, approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l1",))
    provider = DeterministicFakeProvider(provider_name="fake", sections=() if failure else (candidate,), failure=failure)
    return render_with_fallback(rendering_input(), policy(), provider)


def case(scenario_id="scenario-1", *, text="When the condition applies, you pay 10% of the claim amount.", failure=None):
    return build_case(case_id=f"case-{scenario_id}", scenario_id=scenario_id, result=result(text=text, failure=failure))


def test_readability_signals_counts_words():
    assert readability_signals("You pay 10%.").word_count == 3


def test_readability_signals_counts_sentences():
    assert readability_signals("One. Two!").sentence_count == 2


def test_readability_signals_counts_legalistic_terms():
    assert readability_signals("The insured shall bear the amount.").legalistic_term_count == 2


def test_readability_rejects_empty_text():
    with pytest.raises(LLMBaselineError):
        readability_signals(" ")


def test_build_case_requires_result():
    with pytest.raises(LLMBaselineError):
        build_case(case_id="c", scenario_id="s", result=object())


def test_evaluate_case_releases_verified_wording():
    outcome = evaluate_case(case())
    assert outcome.outcome_status == "RELEASED"


def test_released_case_preserves_section_count():
    outcome = evaluate_case(case())
    assert outcome.released_section_count == outcome.deterministic_section_count == 1


def test_released_case_records_fidelity():
    assert evaluate_case(case()).fidelity_status == "VERIFIED"


def test_released_case_records_provider_status():
    assert evaluate_case(case()).provider_status == "SUCCEEDED"


def test_readability_improvement_detected():
    assert evaluate_case(case()).readability_improved_section_count == 1


def test_unchanged_wording_not_marked_improved():
    source = "When the condition is applicable, the insured shall bear 10% of the admissible claim amount."
    assert evaluate_case(case(text=source)).readability_improved_section_count == 0


def test_provider_failure_is_visible():
    outcome = evaluate_case(case(failure="ERROR"))
    assert outcome.outcome_status == "PROVIDER_FAILED"


def test_provider_failure_records_reason():
    assert evaluate_case(case(failure="ERROR")).fallback_reason == "PROVIDER_ERROR"


def test_fallback_releases_deterministic_text():
    outcome = evaluate_case(case(failure="ERROR"))
    assert outcome.section_comparisons[0].released_text == outcome.section_comparisons[0].deterministic_text


def test_fallback_not_marked_readability_improved():
    assert evaluate_case(case(failure="ERROR")).readability_improved_section_count == 0


def test_report_pass_when_all_released():
    report = evaluate_hybrid_baseline((case("b"), case("a")))
    assert report.report_status == "PASS"


def test_report_orders_scenarios_deterministically():
    report = evaluate_hybrid_baseline((case("b"), case("a")))
    assert [item.scenario_id for item in report.scenario_outcomes] == ["a", "b"]


def test_report_mixed_status():
    report = evaluate_hybrid_baseline((case("a"), case("b", failure="ERROR")))
    assert report.report_status == "MIXED"


def test_report_fallback_only_status():
    report = evaluate_hybrid_baseline((case("a", failure="ERROR"),))
    assert report.report_status == "FALLBACK_ONLY"


def test_report_rates_are_explicit():
    report = evaluate_hybrid_baseline((case("a"), case("b", failure="ERROR")))
    assert report.release_rate == .5 and report.fallback_rate == .5


def test_report_fidelity_pass_rate():
    report = evaluate_hybrid_baseline((case("a"), case("b", failure="ERROR")))
    assert report.fidelity_pass_rate == .5


def test_report_map_is_keyed_by_scenario():
    report = evaluate_hybrid_baseline((case("a"),))
    assert report.scenario_outcome_map["a"].scenario_id == "a"


def test_duplicate_scenario_rejected():
    with pytest.raises(LLMBaselineError):
        evaluate_hybrid_baseline((case("a"), case("a")))


def test_empty_report_rejected():
    with pytest.raises(LLMBaselineError):
        evaluate_hybrid_baseline(())


def test_report_identity_is_deterministic():
    first = evaluate_hybrid_baseline((case("a"), case("b")))
    second = evaluate_hybrid_baseline((case("b"), case("a")))
    assert first.report_id == second.report_id


def test_report_is_frozen():
    report = evaluate_hybrid_baseline((case("a"),))
    assert isinstance(report, HybridBaselineReport)
    with pytest.raises(FrozenInstanceError):
        report.report_status = "MIXED"
