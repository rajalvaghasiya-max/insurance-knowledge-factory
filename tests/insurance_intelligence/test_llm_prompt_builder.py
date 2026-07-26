from dataclasses import FrozenInstanceError
import json

import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet, build_clarification_requirement,
    build_finding_disposition, build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import (
    build_fidelity_check, build_output as build_explanation_output,
    build_section,
)
from insurance_intelligence.contracts.llm_rendering import build_input
from insurance_intelligence.llm.policy import build_renderer_policy
from insurance_intelligence.llm.prompt_builder import (
    MANDATORY_PROHIBITIONS, SYSTEM_INSTRUCTION, PromptBuilderError,
    build_prompt_packet, build_prompt_request,
)


def decision():
    packet = build_approved_response_packet(packet_id="p", approved_finding_ids=("f1",), approved_evidence_ids=("e1",), limitation_ids=("l1",), prohibited_operations=("RECOMMEND",))
    disposition = build_finding_disposition(finding_id="f1", disposition="APPROVED_WITH_LIMITATIONS", basis="supported", approved_evidence_ids=("e1",), limitation_ids=("l1",), confidence=.9)
    return build_decision_output(request_id="r1", decision_id="d1", decision="APPROVED_WITH_LIMITATIONS", finding_dispositions=(disposition,), response_packet=packet, limitations=("Condition applies.",), confidence=.9)


def explanation(*, extra_section=None):
    s1 = build_section(section_id="s1", section_type="MEANING", status="DRAFTED", text="When the condition applies, the insured pays 10%.", approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l1",))
    check = build_fidelity_check(check_id="c1", check_type="NO_NEW_FACTS", status="PASSED", description="ok", section_ids=("s1",))
    sections = (s1,) if extra_section is None else (s1, extra_section)
    return build_explanation_output(request_id="r1", explanation_id="x1", audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="CLAUSE_MEANING", sections=sections, fidelity_checks=(check,), fidelity_status="VERIFIED", limitations=("Condition applies.",), explanation_status="DRAFTED_WITH_LIMITATIONS", confidence=.9)


def rendering_input(style=None):
    return build_input(request_id="r1", decision_output=decision(), deterministic_explanation=explanation(), provider_name="fake", model_name="model", style_context=style)


def policy():
    return build_renderer_policy(provider_name="fake", allowed_models=("model",), default_model="model", maximum_temperature=.2, maximum_output_tokens=500)


def clarification_input():
    clarification = build_clarification_requirement(clarification_id="q1", topic="copay", question_key="trigger", reason="missing", priority="HIGH", required_context_keys=("trigger",))
    d = build_decision_output(request_id="r1", decision_id="d2", decision="CLARIFICATION_REQUIRED", clarifications=(clarification,), confidence=.4)
    s = build_section(section_id="sq", section_type="CLARIFICATION", status="DRAFTED", text="Please confirm whether the trigger applies.", clarification_ids=("q1",))
    x = build_explanation_output(request_id="r1", explanation_id="xq", audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="CLARIFICATION_REQUEST", sections=(s,), fidelity_status="VERIFIED", explanation_status="CLARIFICATION_DRAFTED", confidence=.4)
    return build_input(request_id="r1", decision_output=d, deterministic_explanation=x, provider_name="fake", model_name="model")


def test_packet_contains_only_drafted_source_text():
    item = build_prompt_packet(rendering_input())
    assert [s.text for s in item.source_sections] == ["When the condition applies, the insured pays 10%."]


def test_packet_preserves_finding_evidence_limitation_ids():
    s = build_prompt_packet(rendering_input()).source_sections[0]
    assert (s.approved_finding_ids, s.evidence_ids, s.limitation_ids) == (("f1",), ("e1",), ("l1",))


def test_packet_preserves_audience_controls():
    item = build_prompt_packet(rendering_input())
    assert (item.audience, item.reading_level, item.explanation_mode) == ("CUSTOMER", "SIMPLE", "CLAUSE_MEANING")


def test_packet_includes_deterministic_limitations():
    assert build_prompt_packet(rendering_input()).limitations == ("Condition applies.",)


def test_packet_has_mandatory_prohibitions():
    item = build_prompt_packet(rendering_input())
    assert set(MANDATORY_PROHIBITIONS) <= set(item.prohibited_operations)


def test_packet_preserves_decision_prohibition():
    assert "RECOMMEND" in build_prompt_packet(rendering_input()).prohibited_operations


def test_system_instruction_forbids_new_content():
    assert "Do not add reasoning" in SYSTEM_INSTRUCTION


def test_prompt_identity_is_deterministic():
    assert build_prompt_packet(rendering_input()).prompt_packet_id == build_prompt_packet(rendering_input()).prompt_packet_id


def test_prompt_identity_changes_with_style():
    assert build_prompt_packet(rendering_input({"tone":"plain"})).prompt_packet_id != build_prompt_packet(rendering_input({"tone":"formal"})).prompt_packet_id


def test_canonical_payload_is_valid_json():
    json.loads(build_prompt_packet(rendering_input()).canonical_payload)


def test_canonical_payload_uses_stable_key_order():
    item = build_prompt_packet(rendering_input({"tone":"plain", "locale":"en-IN"}))
    assert item.canonical_payload.index('"locale"') < item.canonical_payload.index('"tone"')


def test_style_controls_are_immutable():
    item = build_prompt_packet(rendering_input({"tone":"plain"}))
    with pytest.raises(TypeError):
        item.style_controls["tone"] = "other"


def test_rejects_unknown_style_control():
    with pytest.raises(PromptBuilderError, match="unsupported style"):
        build_prompt_packet(rendering_input({"repository_path":"secret"}))


def test_rejects_nested_style_control():
    with pytest.raises(PromptBuilderError, match="scalar"):
        build_prompt_packet(rendering_input({"tone":{"value":"plain"}}))


def test_prompt_packet_is_frozen():
    item = build_prompt_packet(rendering_input())
    with pytest.raises(FrozenInstanceError):
        item.audience = "ADVISOR"


def test_withheld_section_is_excluded():
    withheld = build_section(section_id="s2", section_type="INTERNAL_REVIEW_NOTE", status="WITHHELD", text="hidden")
    inp = build_input(request_id="r1", decision_output=decision(), deterministic_explanation=explanation(extra_section=withheld), provider_name="fake", model_name="model")
    assert tuple(s.section_id for s in build_prompt_packet(inp).source_sections) == ("s1",)


def test_rejects_unapproved_finding_exposure():
    bad = build_section(section_id="s2", section_type="MEANING", status="DRAFTED", text="bad", approved_finding_ids=("f2",), evidence_ids=("e1",))
    inp = build_input(request_id="r1", decision_output=decision(), deterministic_explanation=explanation(extra_section=bad), provider_name="fake", model_name="model")
    with pytest.raises(PromptBuilderError, match="unapproved finding"):
        build_prompt_packet(inp)


def test_rejects_unapproved_evidence_exposure():
    bad = build_section(section_id="s2", section_type="MEANING", status="DRAFTED", text="bad", approved_finding_ids=("f1",), evidence_ids=("e2",))
    inp = build_input(request_id="r1", decision_output=decision(), deterministic_explanation=explanation(extra_section=bad), provider_name="fake", model_name="model")
    with pytest.raises(PromptBuilderError, match="unapproved evidence"):
        build_prompt_packet(inp)


def test_rejects_unapproved_limitation_exposure():
    bad = build_section(section_id="s2", section_type="LIMITATION", status="DRAFTED", text="bad", approved_finding_ids=("f1",), evidence_ids=("e1",), limitation_ids=("l2",))
    inp = build_input(request_id="r1", decision_output=decision(), deterministic_explanation=explanation(extra_section=bad), provider_name="fake", model_name="model")
    with pytest.raises(PromptBuilderError, match="unapproved limitation"):
        build_prompt_packet(inp)


def test_clarification_packet_contains_no_findings_or_evidence():
    item = build_prompt_packet(clarification_input())
    assert item.source_sections[0].approved_finding_ids == ()
    assert item.source_sections[0].evidence_ids == ()


def test_clarification_identity_is_preserved():
    assert build_prompt_packet(clarification_input()).source_sections[0].clarification_ids == ("q1",)


def test_build_request_enforces_provider_and_model_policy():
    built = build_prompt_request(rendering_input(), policy())
    assert built.provider_request.provider_name == "fake"
    assert built.provider_request.model_name == "model"


def test_build_request_disables_tools_browsing_memory():
    request = build_prompt_request(rendering_input(), policy()).provider_request
    assert not request.tools_enabled and not request.browsing_enabled and not request.memory_enabled


def test_build_request_requires_structured_output():
    assert build_prompt_request(rendering_input(), policy()).provider_request.structured_output


def test_build_request_identity_is_deterministic():
    assert build_prompt_request(rendering_input(), policy()).provider_request == build_prompt_request(rendering_input(), policy()).provider_request
