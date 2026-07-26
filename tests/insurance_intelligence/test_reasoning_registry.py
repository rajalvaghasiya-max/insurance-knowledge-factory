from __future__ import annotations

import pytest

from insurance_intelligence.reasoning.registry import (
    ReasoningRuleRegistry,
    RuleRegistryError,
    build_rule_definition,
)


def rule(**overrides):
    values = {
        "rule_id": "conditional_copayment_obligation_v1",
        "rule_version": "1.0",
        "domain": "health",
        "topic": "conditional_copayment",
        "supported_requirement_types": ("DERIVE_INSURANCE_IMPLICATIONS",),
        "required_evidence_topics": ("conditional_copayment",),
        "required_evidence_roles": ("DEFINING",),
        "required_authority": "AUTHORITATIVE",
        "required_inputs": (),
        "output_finding_types": ("CLAIM_COST_SHARING",),
        "execution_priority": 20,
    }
    values.update(overrides)
    return build_rule_definition(**values)


def test_build_rule_definition_preserves_versioned_metadata():
    item = rule()
    assert item.registry_key == ("conditional_copayment_obligation_v1", "1.0")
    assert item.output_finding_types == ("CLAIM_COST_SHARING",)
    assert item.execution_priority == 20


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("domain", "property"),
        ("topic", "premium"),
        ("required_authority", "UNTRUSTED"),
        ("required_evidence_roles", ("INVENTED",)),
        ("output_finding_types", ("RECOMMENDATION",)),
        ("execution_priority", -1),
    ],
)
def test_invalid_governed_metadata_is_rejected(field, value):
    with pytest.raises(RuleRegistryError):
        rule(**{field: value})


def test_empty_requirement_types_and_findings_are_rejected():
    with pytest.raises(RuleRegistryError):
        rule(supported_requirement_types=())
    with pytest.raises(RuleRegistryError):
        rule(output_finding_types=())


def test_duplicate_values_in_metadata_are_rejected():
    with pytest.raises(RuleRegistryError):
        rule(required_inputs=("treatment_city", "treatment_city"))


def test_registry_rejects_duplicate_registration():
    item = rule()
    registry = ReasoningRuleRegistry((item,))
    with pytest.raises(RuleRegistryError, match="duplicate rule registration"):
        registry.register(item)


def test_registry_rejects_ambiguous_rule_id_even_with_other_version():
    registry = ReasoningRuleRegistry((rule(),))
    with pytest.raises(RuleRegistryError, match="ambiguous duplicate rule_id"):
        registry.register(rule(rule_version="2.0"))


def test_registry_preserves_deterministic_priority_order():
    high = rule(rule_id="z_rule", execution_priority=10)
    low = rule(rule_id="a_rule", execution_priority=20)
    tie = rule(rule_id="b_rule", execution_priority=20)
    registry = ReasoningRuleRegistry((low, tie, high))
    assert [item.rule_id for item in registry.all_rules()] == ["z_rule", "a_rule", "b_rule"]


def test_registry_get_requires_registered_identity():
    registry = ReasoningRuleRegistry((rule(),))
    assert registry.get("conditional_copayment_obligation_v1").rule_version == "1.0"
    assert registry.get("conditional_copayment_obligation_v1", "1.0").domain == "health"
    with pytest.raises(RuleRegistryError):
        registry.get("missing")


def test_eligible_rules_match_all_governed_dimensions():
    registry = ReasoningRuleRegistry((rule(),))
    matches = registry.eligible_rules(
        domain="health",
        topic="conditional_copayment",
        requirement_type="DERIVE_INSURANCE_IMPLICATIONS",
        available_evidence_topics=("conditional_copayment",),
        available_evidence_roles=("DEFINING", "SUPPORTING"),
        available_authorities=("AUTHORITATIVE",),
    )
    assert [item.rule_id for item in matches] == ["conditional_copayment_obligation_v1"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"domain": "motor"},
        {"topic": "copay"},
        {"requirement_type": "COMPARE_OPTIONS"},
        {"available_evidence_topics": ()},
        {"available_evidence_roles": ("SUPPORTING",)},
        {"available_authorities": ("SUPPORTING",)},
    ],
)
def test_eligible_rules_fail_closed_when_any_dimension_is_missing(overrides):
    arguments = {
        "domain": "health",
        "topic": "conditional_copayment",
        "requirement_type": "DERIVE_INSURANCE_IMPLICATIONS",
        "available_evidence_topics": ("conditional_copayment",),
        "available_evidence_roles": ("DEFINING",),
        "available_authorities": ("AUTHORITATIVE",),
    }
    arguments.update(overrides)
    assert ReasoningRuleRegistry((rule(),)).eligible_rules(**arguments) == ()


def test_required_inputs_must_be_explicitly_available():
    registry = ReasoningRuleRegistry((rule(required_inputs=("treatment_city",)),))
    base = {
        "domain": "health",
        "topic": "conditional_copayment",
        "requirement_type": "DERIVE_INSURANCE_IMPLICATIONS",
        "available_evidence_topics": ("conditional_copayment",),
        "available_evidence_roles": ("DEFINING",),
        "available_authorities": ("AUTHORITATIVE",),
    }
    assert registry.eligible_rules(**base) == ()
    assert len(registry.eligible_rules(**base, available_inputs=("treatment_city",))) == 1


def test_any_topic_rule_can_match_specific_topic():
    registry = ReasoningRuleRegistry((rule(rule_id="direct_fact", topic="any"),))
    matches = registry.eligible_rules(
        domain="health",
        topic="conditional_copayment",
        requirement_type="DERIVE_INSURANCE_IMPLICATIONS",
        available_evidence_topics=("conditional_copayment",),
        available_evidence_roles=("DEFINING",),
        available_authorities=("ANY_GOVERNED",),
    )
    assert [item.rule_id for item in matches] == ["direct_fact"]


def test_registry_does_not_execute_rules():
    item = rule()
    assert not hasattr(item, "execute")
    assert not hasattr(ReasoningRuleRegistry((item,)), "execute")
