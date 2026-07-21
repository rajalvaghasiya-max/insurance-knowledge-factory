from dataclasses import FrozenInstanceError, replace

import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_clarification_requirement,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import (
    build_input,
    build_section,
    build_terminology_substitution,
)
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.validator import (
    ExplanationValidationError,
    validate_explanation_fidelity,
)


def finding(*, finding_id="finding-1", condition="treatment occurs in the specified city category"):
    return build_finding(
        finding_id=finding_id,
        requirement_id="requirement-1",
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect="10% of the admissible claim amount",
        condition=condition,
        scope="star_health:star_comprehensive",
        finding_status="SUPPORTED",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        evidence_ids=("evidence-1",),
        limitations=("limitation-1",),
        confidence=0.95,
    )


def decision(*, approved=True, extra_disposition=()):
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
        basis="Supported with condition preserved.",
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        confidence=0.95,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED_WITH_LIMITATIONS" if approved else "APPROVED",
        finding_dispositions=(disposition,) + tuple(extra_disposition),
        response_packet=packet,
        limitations=("Condition must remain explicit.",) if approved else (),
        confidence=0.9,
    )


def explanation_input():
    return build_input(request_id="request-1", decision_output=decision())


def valid_sections():
    return (
        build_section(
            section_id="meaning-1",
            section_type="MEANING",
            status="DRAFTED",
            text="When treatment occurs in the specified city category, you must bear 10% of the admissible claim amount.",
            approved_finding_ids=("finding-1",),
            evidence_ids=("evidence-1",),
            limitation_ids=("limitation-1",),
        ),
        build_section(
            section_id="condition-1",
            section_type="CONDITION",
            status="DRAFTED",
            text="This applies only when treatment occurs in the specified city category.",
            approved_finding_ids=("finding-1",),
            evidence_ids=("evidence-1",),
        ),
        build_section(
            section_id="limit-1",
            section_type="LIMITATION",
            status="DRAFTED",
            text="The condition must remain explicit.",
            limitation_ids=("limitation-1",),
        ),
    )


def validate(sections=None, **kwargs):
    return validate_explanation_fidelity(
        explanation_input=kwargs.pop("input_value", explanation_input()),
        sections=valid_sections() if sections is None else sections,
        findings_by_id=kwargs.pop("findings", {"finding-1": finding()}),
        terminology_substitutions=kwargs.pop("terminology", ()),
    )


def test_valid_draft_is_verified_with_limitations():
    result = validate()
    assert result.validation_status == "VERIFIED_WITH_LIMITATIONS"
    assert result.fidelity_status == "VERIFIED_WITH_LIMITATIONS"
    assert result.confidence == 0.9


def test_checks_are_deterministically_ordered():
    result = validate()
    assert result.checks == tuple(sorted(result.checks, key=lambda item: (item.check_type, item.check_id)))


def test_missing_condition_fails():
    sections = (replace(valid_sections()[0], text="You must bear 10% of the admissible claim amount."), valid_sections()[2])
    assert validate(sections).validation_status == "FAILED_MISSING_CONDITION"


def test_numeric_change_fails():
    sections = tuple(replace(item, text=item.text.replace("10%", "20%")) for item in valid_sections())
    assert validate(sections).validation_status == "FAILED_NUMERIC_CHANGE"


def test_new_numeric_term_fails():
    sections = (replace(valid_sections()[0], text=valid_sections()[0].text + " This applies for 30 days."),) + valid_sections()[1:]
    assert validate(sections).validation_status == "FAILED_NUMERIC_CHANGE"


def test_missing_limitation_fails():
    sections = tuple(item for item in valid_sections() if item.section_type != "LIMITATION")
    sections = tuple(replace(item, limitation_ids=()) for item in sections)
    assert validate(sections).validation_status == "FAILED_MISSING_LIMITATION"


def test_missing_evidence_reference_fails():
    section = build_section(
        section_id="limit-only",
        section_type="LIMITATION",
        status="DRAFTED",
        text="Treatment occurs in the specified city category and 10% applies.",
        limitation_ids=("limitation-1",),
    )
    assert validate((section,)).validation_status == "FAILED_DECISION_SCOPE"


def test_evidence_failure_is_detected_when_finding_is_still_covered():
    section = replace(valid_sections()[0], evidence_ids=())
    with pytest.raises(Exception):
        # Contract itself prevents drafted finding-backed content without evidence.
        build_section(
            section_id="unsafe",
            section_type="MEANING",
            status="DRAFTED",
            text=section.text,
            approved_finding_ids=("finding-1",),
            evidence_ids=(),
        )


def test_missing_approved_finding_map_fails_closed():
    with pytest.raises(ExplanationValidationError, match="missing"):
        validate(findings={})


def test_recommendation_language_fails():
    sections = (replace(valid_sections()[0], text=valid_sections()[0].text + " You should buy this policy."),) + valid_sections()[1:]
    assert validate(sections).validation_status == "FAILED_UNSUPPORTED_CONTENT"


def test_suitability_language_fails():
    sections = (replace(valid_sections()[0], text=valid_sections()[0].text + " This is the best plan for you."),) + valid_sections()[1:]
    assert validate(sections).validation_status == "FAILED_UNSUPPORTED_CONTENT"


def test_new_currency_calculation_fails():
    sections = (replace(valid_sections()[0], text=valid_sections()[0].text + " You will pay ₹5,000."),) + valid_sections()[1:]
    assert validate(sections).validation_status == "FAILED_UNSUPPORTED_CONTENT"


def test_meaning_changing_terminology_fails():
    term = build_terminology_substitution(
        substitution_id="term-1",
        source_term="conditional co-payment",
        rendered_term="always payable amount",
        action="SIMPLIFY",
        approved_finding_ids=("finding-1",),
        meaning_preserved=False,
    )
    assert validate(terminology=(term,)).validation_status == "FAILED_UNSUPPORTED_CONTENT"


def test_meaning_preserving_terminology_passes():
    term = build_terminology_substitution(
        substitution_id="term-1",
        source_term="admissible claim amount",
        rendered_term="eligible claim amount",
        action="SIMPLIFY",
        approved_finding_ids=("finding-1",),
        meaning_preserved=True,
    )
    assert validate(terminology=(term,)).fidelity_status == "VERIFIED_WITH_LIMITATIONS"


def test_withheld_finding_cannot_be_exposed():
    withheld = build_finding_disposition(
        finding_id="finding-2",
        disposition="WITHHELD_UNSUPPORTED",
        basis="Unsupported.",
        confidence=0.1,
    )
    input_value = build_input(request_id="request-1", decision_output=decision(extra_disposition=(withheld,)))
    leaked = build_section(
        section_id="leak",
        section_type="MEANING",
        status="DRAFTED",
        text="The product is suitable.",
        approved_finding_ids=("finding-2",),
        evidence_ids=("evidence-2",),
    )
    result = validate(valid_sections() + (leaked,), input_value=input_value)
    assert result.validation_status == "FAILED_DECISION_SCOPE"


def clarification_input():
    clarification = build_clarification_requirement(
        clarification_id="clarification-1",
        topic="conditional_copayment",
        question_key="trigger_status",
        reason="Please confirm whether the documented trigger applies.",
        priority="HIGH",
        required_context_keys=("trigger_status",),
    )
    output = build_decision_output(
        request_id="request-1",
        decision_id="decision-c",
        decision="CLARIFICATION_REQUIRED",
        clarifications=(clarification,),
        confidence=0.4,
    )
    return build_input(
        request_id="request-1",
        decision_output=output,
        explanation_mode="CLARIFICATION_REQUEST",
    )


def test_valid_clarification_is_verified():
    section = build_section(
        section_id="clarify-1",
        section_type="CLARIFICATION",
        status="DRAFTED",
        text="Did the documented trigger apply?",
        clarification_ids=("clarification-1",),
    )
    result = validate_explanation_fidelity(
        explanation_input=clarification_input(), sections=(section,), findings_by_id={}
    )
    assert result.validation_status == "VERIFIED"


def test_missing_clarification_id_fails_contract_before_validation():
    with pytest.raises(Exception):
        build_section(
            section_id="clarify-1",
            section_type="CLARIFICATION",
            status="DRAFTED",
            text="Did the documented trigger apply?",
        )


def test_extra_ordinary_section_in_clarification_fails():
    clarification = build_section(
        section_id="clarify-1",
        section_type="CLARIFICATION",
        status="DRAFTED",
        text="Did the documented trigger apply?",
        clarification_ids=("clarification-1",),
    )
    ordinary = build_section(
        section_id="meaning-2",
        section_type="MEANING",
        status="DRAFTED",
        text="You should buy this policy.",
    )
    result = validate_explanation_fidelity(
        explanation_input=clarification_input(), sections=(clarification, ordinary), findings_by_id={}
    )
    assert result.validation_status == "FAILED_CLARIFICATION_FIDELITY"


def test_clarification_recommendation_fails_unsupported_content():
    section = build_section(
        section_id="clarify-1",
        section_type="CLARIFICATION",
        status="DRAFTED",
        text="Please confirm the trigger, and you should buy this policy.",
        clarification_ids=("clarification-1",),
    )
    result = validate_explanation_fidelity(
        explanation_input=clarification_input(), sections=(section,), findings_by_id={}
    )
    assert result.validation_status == "FAILED_UNSUPPORTED_CONTENT"


def test_validation_result_is_immutable():
    result = validate()
    with pytest.raises(FrozenInstanceError):
        result.confidence = 0.1


def test_input_sections_are_not_mutated():
    sections = valid_sections()
    before = tuple(item.text for item in sections)
    validate(sections)
    assert tuple(item.text for item in sections) == before


def test_identical_inputs_produce_identical_result():
    assert validate() == validate()


def test_invalid_input_type_fails():
    with pytest.raises(ExplanationValidationError, match="explanation_input"):
        validate_explanation_fidelity(explanation_input=object(), sections=(), findings_by_id={})
