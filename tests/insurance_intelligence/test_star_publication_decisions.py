from __future__ import annotations

from insurance_intelligence.publication_decision.star_health import (
    build_all_star_publication_decisions,
    build_star_bariatric_surgery_publication_decision,
    build_star_conditional_copayment_publication_decision,
    build_star_room_rent_publication_decision,
)


def test_all_three_star_rules_have_explicit_decisions():
    decisions = build_all_star_publication_decisions()
    assert len(decisions) == 3
    assert {item.certification_id for item in decisions} == {
        "star_comprehensive_conditional_copayment",
        "star_comprehensive_room_rent",
        "star_comprehensive_bariatric_surgery",
    }
    assert {item.decision_status for item in decisions} <= {
        "PUBLISH",
        "WITHHOLD",
        "BLOCKED",
    }


def test_conditional_copayment_is_withheld_while_bound_not_published():
    decision = build_star_conditional_copayment_publication_decision()
    assert decision.certification_outcome == "PASS"
    assert decision.requested_status == "WITHHOLD"
    assert decision.decision_status == "WITHHOLD"
    assert decision.publication_permitted is False
    assert any("bound_not_published" in item for item in decision.limitations)
    assert decision.failures == ()


def test_room_rent_is_approved_for_publication_decision_only():
    decision = build_star_room_rent_publication_decision()
    assert decision.certification_outcome == "PASS"
    assert decision.requested_status == "PUBLISH"
    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.authoritative_publication_created is False
    assert decision.failures == ()


def test_bariatric_rule_is_approved_with_safety_limitations_preserved():
    decision = build_star_bariatric_surgery_publication_decision()
    assert decision.certification_outcome == "PASS"
    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.authoritative_publication_created is False
    assert any("medical suitability" in item for item in decision.limitations)
    assert any("claim admissibility or payment" in item for item in decision.limitations)
    assert decision.failures == ()


def test_each_decision_preserves_certification_and_evidence_trace():
    for decision in build_all_star_publication_decisions():
        assert decision.certification_trace_references
        assert decision.evidence_trace_references
        assert len(decision.evidence_trace_references) == 5
        assert decision.decision_reasons
        assert decision.decision_authority


def test_star_decisions_are_deterministic_and_stably_ordered():
    first = build_all_star_publication_decisions()
    second = build_all_star_publication_decisions()
    assert first == second
    assert [item.topic_id for item in first] == [
        "conditional_obligation",
        "coverage_limit",
        "eligibility_and_consequence",
    ]


def test_no_decision_claims_authoritative_publication_or_claim_payment():
    for decision in build_all_star_publication_decisions():
        assert decision.authoritative_publication_created is False
        assert not hasattr(decision, "claim_payment_guaranteed")
        assert not hasattr(decision, "final_answer")
        assert not hasattr(decision, "recommendation")
