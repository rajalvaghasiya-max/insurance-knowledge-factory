from datetime import date

import pytest

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import RESTORATION_CONCEPT_ID
from insurance_intelligence.benefits.explanation_projection import (
    project_comparison_explanation,
)
from insurance_intelligence.benefits.governed_handoff import (
    GovernedComparisonHandoff,
    GovernedHandoffError,
    build_governed_comparison_handoff,
)
from insurance_intelligence.benefits.orchestration import (
    GovernedComparisonRequest,
    orchestrate_governed_comparison,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import build_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.registry import build_style_definition
from insurance_intelligence.explanation.templates import render_explanation_templates


AS_OF = date(2026, 8, 1)


def _star_copayment_finding():
    return build_finding(
        finding_id="finding-star-copayment",
        requirement_id="requirement-star-copayment",
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect="10% of the admissible claim amount",
        condition="for Insured Persons whose age at the time of entry is 61 years and above",
        trigger="for Insured Persons whose age at the time of entry is 61 years and above",
        exception=(
            "This co-payment will not apply for those insured persons who have entered the policy before "
            "attaining 61 years of age and renew the policy continuously without any break"
        ),
        applicability_scope=(
            "This co-payment is applicable for Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, II.8, "
            "II.9, II.10, II.11, II.15 and II.25"
        ),
        scope="star_health:star_comprehensive",
        finding_status="SUPPORTED",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        evidence_ids=("evidence-star-policy-wording",),
        limitations=("limitation-star-copayment",),
        confidence=0.95,
    )


def _star_explanation_input():
    packet = build_approved_response_packet(
        packet_id="packet-star-copayment",
        approved_finding_ids=("finding-star-copayment",),
        approved_evidence_ids=("evidence-star-policy-wording",),
        limitation_ids=("limitation-star-copayment",),
        prohibited_operations=("RECOMMEND", "RANK"),
    )
    disposition = build_finding_disposition(
        finding_id="finding-star-copayment",
        disposition="APPROVED_WITH_LIMITATIONS",
        basis="Policy wording supports the conditional obligation with exception and scope.",
        approved_evidence_ids=("evidence-star-policy-wording",),
        limitation_ids=("limitation-star-copayment",),
        confidence=0.95,
    )
    decision = build_decision_output(
        request_id="request-star-copayment",
        decision_id="decision-star-copayment",
        decision="APPROVED_WITH_LIMITATIONS",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=("The policy wording conditions must remain explicit.",),
        confidence=0.95,
    )
    return build_input(
        request_id="request-star-copayment",
        decision_output=decision,
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE",
    )


def test_rendered_star_copayment_preserves_trigger_obligation_exception_and_scope():
    finding = _star_copayment_finding()
    explanation_input = _star_explanation_input()
    style = build_style_definition(
        style_id="customer-simple-structural-regression",
        style_version="1.0",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_modes=("PLAIN_LANGUAGE",),
        preserve_conditions=True,
        preserve_limitations=True,
        preserve_evidence_notes=True,
        max_section_words=160,
    )

    rendered = render_explanation_templates(
        explanation_input=explanation_input,
        findings_by_id={finding.finding_id: finding},
        style=style,
    )
    meaning = next(section for section in rendered.sections if section.section_type == "MEANING")
    normalized = meaning.text.lower()

    assert "trigger:" in normalized
    assert "61 years and above" in normalized
    assert "obligation:" in normalized
    assert "10% of the admissible claim amount" in normalized
    assert "exception:" in normalized
    assert "before attaining 61 years of age" in normalized
    assert "scope:" in normalized
    assert "sections ii.1" in normalized
    assert meaning.approved_finding_ids == (finding.finding_id,)
    assert meaning.evidence_ids == ("evidence-star-policy-wording",)


def _ready_projection():
    registry = (
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
    )
    request = GovernedComparisonRequest(
        concept_id=RESTORATION_CONCEPT_ID,
        left_implementation_id=STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.implementation_id,
        right_implementation_id=ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.implementation_id,
        as_of=AS_OF,
    )
    return project_comparison_explanation(
        orchestrate_governed_comparison(request, registry=registry)
    )


def test_exact_governed_projection_enters_pre_ranking_handoff():
    projection = _ready_projection()
    handoff = build_governed_comparison_handoff(projection)
    assert isinstance(handoff, GovernedComparisonHandoff)
    assert handoff.projection is projection
    assert handoff.concept_id == RESTORATION_CONCEPT_ID
    assert handoff.as_of == AS_OF


@pytest.mark.parametrize(
    "legacy_payload",
    (
        {"winner": "legacy-product-a", "recommendation": "buy"},
        {"comparison": {"left": "a", "right": "b"}},
        "outputs/legacy_recommendation.json",
        b"serialized historical output",
        object(),
    ),
)
def test_legacy_outputs_cannot_enter_pre_ranking_handoff(legacy_payload):
    with pytest.raises(GovernedHandoffError, match="exact governed"):
        build_governed_comparison_handoff(legacy_payload)


def test_projection_subclass_cannot_bypass_exact_type_guard():
    projection = _ready_projection()

    class HistoricalProjection(type(projection)):
        pass

    legacy = HistoricalProjection(**projection.__dict__)
    with pytest.raises(GovernedHandoffError, match="exact governed"):
        build_governed_comparison_handoff(legacy)


def test_blocked_projection_cannot_enter_pre_ranking_handoff():
    request = GovernedComparisonRequest(
        concept_id=RESTORATION_CONCEPT_ID,
        left_implementation_id="benefit_impl:missing:left",
        right_implementation_id=ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.implementation_id,
        as_of=AS_OF,
    )
    blocked = project_comparison_explanation(
        orchestrate_governed_comparison(
            request,
            registry=(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,),
        )
    )
    with pytest.raises(GovernedHandoffError, match="blocked"):
        build_governed_comparison_handoff(blocked)


def test_governed_comparison_orchestration_rejects_legacy_request_mapping():
    with pytest.raises(Exception, match="GovernedComparisonRequest"):
        orchestrate_governed_comparison(
            {
                "concept_id": RESTORATION_CONCEPT_ID,
                "left": "legacy-a",
                "right": "legacy-b",
            }
        )
