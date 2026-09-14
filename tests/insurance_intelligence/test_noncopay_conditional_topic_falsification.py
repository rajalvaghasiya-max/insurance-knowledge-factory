from insurance_intelligence.reasoning.engine import _topic
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)


def test_certified_waiting_period_evidence_is_not_collapsed_to_documented_fact() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    evidence = case.evidence_output.evidence_packages
    topics = {item.field_or_topic for item in evidence}

    assert {
        "WAITING_PERIOD_DURATION",
        "WAITING_PERIOD_SUBJECT",
        "WAITING_PERIOD_START_BASIS",
        "APPLICABILITY_SCOPE",
        "CONTINUITY_OR_CREDIT_RULE",
        "EXCEPTION_CONDITION",
    } <= topics
    assert not any("copay" in item.field_or_topic.lower() for item in evidence)

    # Frozen non-co-pay conditional genericity gate:
    # certified waiting-period evidence must retain its concept topic rather than
    # being collapsed into the generic direct-fact lane.
    assert _topic(evidence) == "waiting_period"
