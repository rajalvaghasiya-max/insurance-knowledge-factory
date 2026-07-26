from dataclasses import FrozenInstanceError
import pytest

from insurance_intelligence.contracts.decision import build_approved_response_packet, build_finding_disposition, build_output as build_decision_output
from insurance_intelligence.contracts.explanation import build_fidelity_check, build_output as build_explanation_output, build_section
from insurance_intelligence.contracts.llm_rendering import build_input, build_candidate_section
from insurance_intelligence.llm.fidelity import validate_fidelity
from insurance_intelligence.llm.output_parser import ParsedProviderOutput, parse_provider_output
from insurance_intelligence.llm.policy import build_renderer_policy
from insurance_intelligence.llm.prompt_builder import build_prompt_request


def context():
    packet = build_approved_response_packet(packet_id="p", approved_finding_ids=("f1",), approved_evidence_ids=("e1",), limitation_ids=("l1",))
    disposition = build_finding_disposition(finding_id="f1", disposition="APPROVED_WITH_LIMITATIONS", basis="supported", approved_evidence_ids=("e1",), limitation_ids=("l1",), confidence=.9)
    decision = build_decision_output(request_id="r1", decision_id="d1", decision="APPROVED_WITH_LIMITATIONS", finding_dispositions=(disposition,), response_packet=packet, limitations=("Condition applies.",), confidence=.9)
    section = build_section(section_id="s1", section_type="MEANING", status="DRAFTED", text="When the condition applies, the insured pays 10%.", approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l1",))
    check = build_fidelity_check(check_id="c1", check_type="NO_NEW_FACTS", status="PASSED", description="ok", section_ids=("s1",))
    explanation = build_explanation_output(request_id="r1", explanation_id="x1", audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="CLAUSE_MEANING", sections=(section,), fidelity_checks=(check,), fidelity_status="VERIFIED", limitations=("Condition applies.",), explanation_status="DRAFTED_WITH_LIMITATIONS", confidence=.9)
    inp = build_input(request_id="r1", decision_output=decision, deterministic_explanation=explanation, provider_name="fake", model_name="model")
    policy = build_renderer_policy(provider_name="fake", allowed_models=("model",), default_model="model", maximum_temperature=.2, maximum_output_tokens=500)
    return build_prompt_request(inp, policy)


def parsed(text="When the condition applies, you pay 10%.", **overrides):
    built = context()
    section = {"section_id":"cs1", "source_section_id":"s1", "section_type":"MEANING", "text":text, "approved_finding_ids":["f1"], "evidence_ids":["e1"], "limitation_ids":["l1"], "clarification_ids":[]}
    section.update(overrides)
    return built, parse_provider_output({"sections":[section]}, built.provider_request)


def test_verified_candidate_is_accepted():
    built, item = parsed()
    result = validate_fidelity(built.prompt_packet, item)
    assert result.status == "VERIFIED" and result.accepted_sections


def test_result_identity_is_deterministic():
    built, item = parsed()
    assert validate_fidelity(built.prompt_packet, item).validation_id == validate_fidelity(built.prompt_packet, item).validation_id


def test_result_is_frozen():
    built, item = parsed(); result = validate_fidelity(built.prompt_packet, item)
    with pytest.raises(FrozenInstanceError): result.status = "FAILED"


def test_numeric_change_fails():
    built, item = parsed("When the condition applies, you pay 20%.")
    result = validate_fidelity(built.prompt_packet, item)
    assert "NUMERIC_CHANGE" in result.failure_reasons


def test_number_format_equivalence_passes():
    built, item = parsed("When the condition applies, you pay 10.0%.")
    assert validate_fidelity(built.prompt_packet, item).status == "VERIFIED"


def test_missing_condition_fails():
    built, item = parsed("You pay 10%.")
    assert "MISSING_CONDITION" in validate_fidelity(built.prompt_packet, item).failure_reasons


def test_evidence_change_fails():
    built, item = parsed()
    altered = build_candidate_section(section_id="cs1", source_section_id="s1", section_type="MEANING", text="When the condition applies, you pay 10%.", approved_finding_ids=("f1",), evidence_ids=("e2",), limitation_ids=("l1",))
    item = ParsedProviderOutput(parse_id=item.parse_id, provider_request_id=item.provider_request_id, candidate_sections=(altered,), canonical_payload=item.canonical_payload)
    assert "EVIDENCE_MISMATCH" in validate_fidelity(built.prompt_packet, item).failure_reasons


def test_limitation_change_fails():
    built, item = parsed(limitation_ids=[])
    assert "MISSING_LIMITATION" in validate_fidelity(built.prompt_packet, item).failure_reasons


def test_section_type_change_fails_scope():
    built, item = parsed(section_type="RECOMMENDATION")
    assert "DECISION_SCOPE_MISMATCH" in validate_fidelity(built.prompt_packet, item).failure_reasons


def test_recommendation_language_fails():
    built, item = parsed("When the condition applies, you pay 10%, and you should buy this plan.")
    assert "UNSUPPORTED_CONTENT" in validate_fidelity(built.prompt_packet, item).failure_reasons


def test_guarantee_language_fails():
    built, item = parsed("When the condition applies, you pay 10% and the claim will be paid.")
    assert "UNSUPPORTED_CONTENT" in validate_fidelity(built.prompt_packet, item).failure_reasons


def test_failed_result_releases_no_candidate_sections():
    built, item = parsed("You should buy this plan because it is always covered at 20%.")
    result = validate_fidelity(built.prompt_packet, item)
    assert result.status == "FAILED" and result.accepted_sections == ()
