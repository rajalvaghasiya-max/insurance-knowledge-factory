from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_clarification_requirement,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import build_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.generator import (
    ExplanationGenerationError,
    generate_explanation,
)
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    TerminologyRegistry,
    build_style_definition,
    build_terminology_definition,
)


def finding(*, finding_id="finding-1", condition="treatment occurs in the specified city category", limitations=("limitation-1",)):
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
        limitations=limitations,
        confidence=0.95,
    )


def approved_decision(*, limitations=True):
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",) if limitations else (),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED_WITH_LIMITATIONS" if limitations else "APPROVED",
        basis="Supported by governed evidence.",
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",) if limitations else (),
        confidence=0.95,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED_WITH_LIMITATIONS" if limitations else "APPROVED",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=("Condition must remain explicit.",) if limitations else (),
        confidence=0.9,
    )


def clarification_decision():
    clarification = build_clarification_requirement(
        clarification_id="clarification-1",
        question_key="trigger_status",
        topic="conditional_copayment",
        reason="Confirm whether the documented trigger applied to this treatment.",
        required_context_keys=("trigger_status",),
        related_finding_ids=("finding-1",),
        priority="HIGH",
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="WITHHELD_FOR_CLARIFICATION",
        basis="Trigger status is required.",
        clarification_ids=("clarification-1",),
        confidence=0.4,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-clarify",
        decision="CLARIFICATION_REQUIRED",
        finding_dispositions=(disposition,),
        clarifications=(clarification,),
        confidence=0.7,
    )


def styles(*, audience="CUSTOMER", level="SIMPLE", modes=("PLAIN_LANGUAGE",)):
    return ExplanationStyleRegistry((build_style_definition(
        style_id=f"style-{audience.lower()}-{level.lower()}",
        style_version="1.0",
        audience=audience,
        reading_level=level,
        explanation_modes=modes,
        max_section_words=120,
        priority=10,
    ),))


def terms():
    return TerminologyRegistry((build_terminology_definition(
        terminology_id="eligible-claim-amount",
        terminology_version="1.0",
        source_term="admissible claim amount",
        rendered_term="eligible claim amount",
        action="SIMPLIFY",
        audience="CUSTOMER",
        reading_levels=("SIMPLE",),
        explanation_modes=("PLAIN_LANGUAGE",),
        scope="HEALTH",
        priority=10,
    ),))


def test_star_copayment_plain_language_pilot_is_drafted_with_limitations():
    item = build_input(
        request_id="request-1",
        decision_output=approved_decision(),
        communication_context={"domain_scope": "HEALTH"},
    )
    result = generate_explanation(
        explanation_input=item,
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
        terminology_registry=terms(),
    )
    assert result.explanation_status == "DRAFTED_WITH_LIMITATIONS"
    assert result.fidelity_status == "VERIFIED_WITH_LIMITATIONS"
    assert any("10%" in section.text for section in result.sections)
    assert any("treatment occurs" in section.text for section in result.sections)


def test_star_pilot_preserves_evidence_links():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    linked = {e for section in result.sections for e in section.evidence_ids}
    assert "evidence-1" in linked


def test_registered_terminology_is_applied_without_changing_meaning():
    result = generate_explanation(
        explanation_input=build_input(
            request_id="request-1",
            decision_output=approved_decision(),
            communication_context={"domain_scope": "HEALTH"},
        ),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
        terminology_registry=terms(),
    )
    assert any("eligible claim amount" in section.text for section in result.sections)
    assert result.terminology_substitutions[0].meaning_preserved is True


def test_clarification_pilot_produces_only_clarification_content():
    item = build_input(
        request_id="request-1",
        decision_output=clarification_decision(),
        explanation_mode="CLARIFICATION_REQUEST",
        communication_context={"trigger_status": "Did the documented trigger apply to this treatment?"},
    )
    result = generate_explanation(
        explanation_input=item,
        findings_by_id={"finding-1": finding()},
        style_registry=styles(modes=("CLARIFICATION_REQUEST",)),
    )
    assert result.explanation_status == "CLARIFICATION_DRAFTED"
    assert all(section.section_type == "CLARIFICATION" for section in result.sections)
    assert all(not section.approved_finding_ids for section in result.sections)


def test_approved_without_limitations_is_fully_drafted():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision(limitations=False)),
        findings_by_id={"finding-1": finding(limitations=())},
        style_registry=styles(),
    )
    # Finding limitations are harmless unless approved packet requires them.
    assert result.explanation_status == "DRAFTED"
    assert result.fidelity_status == "VERIFIED"


def test_no_eligible_style_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(ExplanationGenerationError, match="no eligible"):
        generate_explanation(
            explanation_input=item,
            findings_by_id={"finding-1": finding()},
            style_registry=styles(audience="ADVISOR"),
        )


def test_missing_approved_finding_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(Exception, match="missing"):
        generate_explanation(explanation_input=item, findings_by_id={}, style_registry=styles())


def test_finding_map_key_mismatch_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(ExplanationGenerationError, match="keys"):
        generate_explanation(
            explanation_input=item,
            findings_by_id={"wrong": finding()},
            style_registry=styles(),
        )


def test_invalid_style_registry_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(ExplanationGenerationError, match="style_registry"):
        generate_explanation(
            explanation_input=item,
            findings_by_id={"finding-1": finding()},
            style_registry=object(),  # type: ignore[arg-type]
        )


def test_invalid_terminology_registry_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(ExplanationGenerationError, match="terminology_registry"):
        generate_explanation(
            explanation_input=item,
            findings_by_id={"finding-1": finding()},
            style_registry=styles(),
            terminology_registry=object(),  # type: ignore[arg-type]
        )


def test_deterministic_output_for_identical_inputs():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    kwargs = dict(
        explanation_input=item,
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    assert generate_explanation(**kwargs) == generate_explanation(**kwargs)


def test_input_order_does_not_change_output():
    f1 = finding()
    item = build_input(request_id="request-1", decision_output=approved_decision())
    one = generate_explanation(explanation_input=item, findings_by_id={"finding-1": f1}, style_registry=styles())
    two = generate_explanation(explanation_input=item, findings_by_id=dict(reversed([("finding-1", f1)])), style_registry=styles())
    assert one == two


def test_trace_sequences_are_ordered_and_unique():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    seq = [event.sequence for event in result.explanation_trace]
    assert seq == sorted(seq)
    assert len(seq) == len(set(seq))


def test_trace_contains_expected_stage_events():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    types = {event.event_type for event in result.explanation_trace}
    assert {"EXPLANATION_STARTED", "APPROVED_PACKET_RECEIVED", "SECTION_CREATED", "FIDELITY_CHECKED", "EXPLANATION_COMPLETED"} <= types


def test_output_is_immutable():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    with pytest.raises(FrozenInstanceError):
        result.explanation_status = "WITHHELD"  # type: ignore[misc]


def test_source_finding_is_not_mutated():
    source = finding()
    before = source
    generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": source},
        style_registry=styles(),
    )
    assert source == before


def test_generator_does_not_create_recommendation_language():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    text = " ".join(section.text.lower() for section in result.sections)
    assert "should buy" not in text
    assert "best plan" not in text


def test_generator_does_not_create_rupee_calculation():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    assert "₹" not in " ".join(section.text for section in result.sections)


def test_generator_preserves_approved_decision_without_modification():
    decision = approved_decision()
    before = decision
    generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=decision),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    assert decision == before


def test_generator_output_has_no_final_answer_or_recommendation_fields():
    result = generate_explanation(
        explanation_input=build_input(request_id="request-1", decision_output=approved_decision()),
        findings_by_id={"finding-1": finding()},
        style_registry=styles(),
    )
    assert not hasattr(result, "final_answer")
    assert not hasattr(result, "recommendation")


def test_advisor_mode_uses_registered_advisor_style():
    item = build_input(
        request_id="request-1",
        decision_output=approved_decision(),
        audience="ADVISOR",
        reading_level="STANDARD",
        explanation_mode="ADVISOR_TALKING_POINTS",
    )
    result = generate_explanation(
        explanation_input=item,
        findings_by_id={"finding-1": finding()},
        style_registry=styles(audience="ADVISOR", level="STANDARD", modes=("ADVISOR_TALKING_POINTS",)),
    )
    assert any(section.section_type == "ADVISOR_TALKING_POINT" for section in result.sections)
