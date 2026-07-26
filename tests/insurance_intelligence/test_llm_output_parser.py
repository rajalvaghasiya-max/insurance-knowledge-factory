from dataclasses import FrozenInstanceError
import json
import pytest

from insurance_intelligence.contracts.decision import build_approved_response_packet, build_finding_disposition, build_output as build_decision_output
from insurance_intelligence.contracts.explanation import build_fidelity_check, build_output as build_explanation_output, build_section
from insurance_intelligence.contracts.llm_rendering import build_input
from insurance_intelligence.llm.output_parser import LLMOutputParseError, parse_provider_output
from insurance_intelligence.llm.policy import build_renderer_policy
from insurance_intelligence.llm.prompt_builder import build_prompt_request


def built():
    packet = build_approved_response_packet(packet_id="p", approved_finding_ids=("f1",), approved_evidence_ids=("e1",), limitation_ids=("l1",))
    disposition = build_finding_disposition(finding_id="f1", disposition="APPROVED_WITH_LIMITATIONS", basis="supported", approved_evidence_ids=("e1",), limitation_ids=("l1",), confidence=.9)
    decision = build_decision_output(request_id="r1", decision_id="d1", decision="APPROVED_WITH_LIMITATIONS", finding_dispositions=(disposition,), response_packet=packet, limitations=("Condition applies.",), confidence=.9)
    section = build_section(section_id="s1", section_type="MEANING", status="DRAFTED", text="When the condition applies, the insured pays 10%.", approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l1",))
    check = build_fidelity_check(check_id="c1", check_type="NO_NEW_FACTS", status="PASSED", description="ok", section_ids=("s1",))
    explanation = build_explanation_output(request_id="r1", explanation_id="x1", audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="CLAUSE_MEANING", sections=(section,), fidelity_checks=(check,), fidelity_status="VERIFIED", limitations=("Condition applies.",), explanation_status="DRAFTED_WITH_LIMITATIONS", confidence=.9)
    inp = build_input(request_id="r1", decision_output=decision, deterministic_explanation=explanation, provider_name="fake", model_name="model")
    policy = build_renderer_policy(provider_name="fake", allowed_models=("model",), default_model="model", maximum_temperature=.2, maximum_output_tokens=500)
    return build_prompt_request(inp, policy)


def payload(**overrides):
    section = {
        "section_id":"cs1", "source_section_id":"s1", "section_type":"MEANING",
        "text":"When the condition applies, you pay 10%.",
        "approved_finding_ids":["f1"], "evidence_ids":["e1"],
        "limitation_ids":["l1"], "clarification_ids":[],
    }
    section.update(overrides)
    return {"sections":[section]}


def test_parses_mapping():
    result = parse_provider_output(payload(), built().provider_request)
    assert result.candidate_sections[0].text.endswith("10%.")


def test_parses_json_text():
    result = parse_provider_output(json.dumps(payload()), built().provider_request)
    assert result.provider_request_id == built().provider_request.provider_request_id


def test_parse_identity_is_deterministic():
    assert parse_provider_output(payload(), built().provider_request).parse_id == parse_provider_output(payload(), built().provider_request).parse_id


def test_canonical_payload_is_stable_json():
    result = parse_provider_output(payload(), built().provider_request)
    assert json.loads(result.canonical_payload)["sections"][0]["section_id"] == "cs1"


def test_result_is_frozen():
    result = parse_provider_output(payload(), built().provider_request)
    with pytest.raises(FrozenInstanceError): result.parse_id = "x"


def test_rejects_invalid_json():
    with pytest.raises(LLMOutputParseError, match="valid JSON"):
        parse_provider_output("{", built().provider_request)


def test_rejects_extra_root_field():
    raw = payload(); raw["comment"] = "x"
    with pytest.raises(LLMOutputParseError, match="only the sections"):
        parse_provider_output(raw, built().provider_request)


def test_rejects_empty_sections():
    with pytest.raises(LLMOutputParseError, match="non-empty"):
        parse_provider_output({"sections":[]}, built().provider_request)


def test_rejects_missing_section_field():
    raw = payload(); del raw["sections"][0]["text"]
    with pytest.raises(LLMOutputParseError, match="invalid fields"):
        parse_provider_output(raw, built().provider_request)


def test_rejects_unknown_source_section():
    with pytest.raises(LLMOutputParseError, match="exactly cover"):
        parse_provider_output(payload(source_section_id="other"), built().provider_request)


def test_rejects_unapproved_evidence():
    with pytest.raises(LLMOutputParseError, match="evidence outside"):
        parse_provider_output(payload(evidence_ids=["e2"]), built().provider_request)


def test_rejects_unapproved_finding():
    with pytest.raises(LLMOutputParseError, match="finding outside"):
        parse_provider_output(payload(approved_finding_ids=["f2"], evidence_ids=["e1"]), built().provider_request)
