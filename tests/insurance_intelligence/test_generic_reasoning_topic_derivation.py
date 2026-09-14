from dataclasses import replace

from insurance_intelligence.reasoning.engine import _topic
from insurance_intelligence.reasoning.registry import RULE_TOPICS
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)
from insurance_intelligence.topic_completeness.catalogue import default_topic_definitions


def test_certified_waiting_period_components_resolve_to_waiting_period_topic() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    evidence = case.evidence_output.evidence_packages

    assert _topic(evidence) == "waiting_period"


def test_shared_component_types_do_not_force_ambiguous_topic() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    selected = tuple(
        item
        for item in case.evidence_output.evidence_packages
        if item.field_or_topic in {"APPLICABILITY_SCOPE", "EXCEPTION_CONDITION"}
    )

    assert len(selected) == 2
    assert _topic(selected) == "documented_fact"


def test_existing_copay_runtime_topic_alias_is_preserved() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    evidence = replace(
        case.evidence_output.evidence_packages[0],
        field_or_topic="conditional_copayment",
    )

    assert _topic((evidence,)) == "conditional_copayment"


def test_reasoning_registry_accepts_every_catalogue_topic() -> None:
    catalogue_topics = {definition.topic_id for definition in default_topic_definitions()}

    assert catalogue_topics <= RULE_TOPICS
