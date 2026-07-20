from __future__ import annotations

import pytest

from insurance_intelligence.decision.registry import (
    SafetyPolicyRegistry,
    SafetyPolicyRegistryError,
    build_policy_definition,
)


def policy(**overrides):
    values = {
        "policy_id": "conditional_copayment_context_required_v1",
        "policy_version": "1.0",
        "domain": "health",
        "topic": "conditional_copayment",
        "finding_types": ("CLAIM_COST_SHARING",),
        "finding_statuses": ("CONDITIONAL",),
        "derivation_types": ("CONDITIONAL_DERIVATION",),
        "reasoning_statuses": ("CONDITIONAL",),
        "reasoning_sufficiency_statuses": ("CONDITIONAL",),
        "evidence_resolution_statuses": ("RESOLVED",),
        "evidence_sufficiency_statuses": ("COMPLETE", "SUFFICIENT"),
        "strict_modes": ("STRICT",),
        "required_context_keys": ("trigger_status",),
        "prohibited_operations": (),
        "issue_type": "MISSING_CONTEXT",
        "severity": "HIGH",
        "finding_disposition": "WITHHELD_FOR_CLARIFICATION",
        "decision_outcome": "CLARIFICATION_REQUIRED",
        "blocking": True,
        "evaluation_priority": 10,
    }
    values.update(overrides)
    return build_policy_definition(**values)


def eligible_arguments(**overrides):
    values = {
        "domain": "health",
        "topic": "conditional_copayment",
        "finding_type": "CLAIM_COST_SHARING",
        "finding_status": "CONDITIONAL",
        "derivation_type": "CONDITIONAL_DERIVATION",
        "reasoning_status": "CONDITIONAL",
        "reasoning_sufficiency": "CONDITIONAL",
        "evidence_resolution_status": "RESOLVED",
        "evidence_sufficiency": "COMPLETE",
        "strict_mode": "STRICT",
        "available_context_keys": ("trigger_status",),
        "requested_operations": (),
    }
    values.update(overrides)
    return values


def test_build_policy_definition_preserves_versioned_metadata():
    item = policy()
    assert item.registry_key == ("conditional_copayment_context_required_v1", "1.0")
    assert item.decision_outcome == "CLARIFICATION_REQUIRED"
    assert item.blocking is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("domain", "property"),
        ("topic", "premium"),
        ("finding_types", ("RECOMMENDATION",)),
        ("finding_statuses", ("CERTAIN",)),
        ("derivation_types", ("FREE_FORM",)),
        ("reasoning_statuses", ("DONE",)),
        ("reasoning_sufficiency_statuses", ("UNKNOWN",)),
        ("evidence_resolution_statuses", ("FOUND",)),
        ("evidence_sufficiency_statuses", ("ENOUGH",)),
        ("issue_type", "INVENTED"),
        ("severity", "SEVERE"),
        ("finding_disposition", "RELEASED"),
        ("decision_outcome", "ALLOW"),
        ("evaluation_priority", -1),
    ],
)
def test_invalid_governed_metadata_is_rejected(field, value):
    with pytest.raises(SafetyPolicyRegistryError):
        policy(**{field: value})


def test_duplicate_metadata_values_are_rejected():
    with pytest.raises(SafetyPolicyRegistryError):
        policy(required_context_keys=("trigger_status", "trigger_status"))


def test_any_mode_cannot_be_combined_with_explicit_modes():
    with pytest.raises(SafetyPolicyRegistryError):
        policy(strict_modes=("ANY", "STRICT"))


def test_blocking_policy_cannot_approve_findings_or_decision():
    with pytest.raises(SafetyPolicyRegistryError):
        policy(finding_disposition="APPROVED")
    with pytest.raises(SafetyPolicyRegistryError):
        policy(decision_outcome="APPROVED")


def test_critical_policy_must_be_blocking():
    with pytest.raises(SafetyPolicyRegistryError):
        policy(severity="CRITICAL", blocking=False)


def test_registry_rejects_duplicate_registration():
    item = policy()
    registry = SafetyPolicyRegistry((item,))
    with pytest.raises(SafetyPolicyRegistryError, match="duplicate policy registration"):
        registry.register(item)


def test_registry_rejects_ambiguous_policy_id_even_with_other_version():
    registry = SafetyPolicyRegistry((policy(),))
    with pytest.raises(SafetyPolicyRegistryError, match="ambiguous duplicate policy_id"):
        registry.register(policy(policy_version="2.0"))


def test_registry_preserves_deterministic_priority_order():
    first = policy(policy_id="z_policy", evaluation_priority=5)
    second = policy(policy_id="a_policy", evaluation_priority=10)
    third = policy(policy_id="b_policy", evaluation_priority=10)
    registry = SafetyPolicyRegistry((third, second, first))
    assert [item.policy_id for item in registry.all_policies()] == ["z_policy", "a_policy", "b_policy"]


def test_registry_get_requires_registered_identity():
    registry = SafetyPolicyRegistry((policy(),))
    assert registry.get("conditional_copayment_context_required_v1").policy_version == "1.0"
    assert registry.get("conditional_copayment_context_required_v1", "1.0").domain == "health"
    with pytest.raises(SafetyPolicyRegistryError):
        registry.get("missing")


def test_eligible_policy_matches_all_governed_dimensions():
    matches = SafetyPolicyRegistry((policy(),)).eligible_policies(**eligible_arguments())
    assert [item.policy_id for item in matches] == ["conditional_copayment_context_required_v1"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"domain": "motor"},
        {"topic": "copay"},
        {"finding_type": "DOCUMENTED_FACT"},
        {"finding_status": "SUPPORTED"},
        {"derivation_type": "DIRECT_FACT"},
        {"reasoning_status": "REASONED"},
        {"reasoning_sufficiency": "COMPLETE"},
        {"evidence_resolution_status": "PARTIALLY_RESOLVED"},
        {"evidence_sufficiency": "PARTIAL"},
        {"strict_mode": "PERMISSIVE"},
        {"available_context_keys": ()},
    ],
)
def test_eligible_policies_fail_closed_when_any_dimension_is_missing(overrides):
    assert SafetyPolicyRegistry((policy(),)).eligible_policies(**eligible_arguments(**overrides)) == ()


def test_any_domain_topic_and_mode_can_match_specific_input():
    item = policy(domain="any", topic="any", strict_modes=("ANY",), required_context_keys=())
    assert len(SafetyPolicyRegistry((item,)).eligible_policies(**eligible_arguments())) == 1


def test_prohibited_operation_policy_matches_only_when_operation_is_requested():
    item = policy(
        policy_id="unsupported_recommendation_v1",
        finding_types=(),
        finding_statuses=(),
        derivation_types=(),
        reasoning_statuses=(),
        reasoning_sufficiency_statuses=(),
        evidence_resolution_statuses=(),
        evidence_sufficiency_statuses=(),
        strict_modes=("ANY",),
        required_context_keys=(),
        prohibited_operations=("RECOMMEND_PRODUCT",),
        issue_type="RECOMMENDATION_WITHOUT_SUITABILITY",
        finding_disposition="WITHHELD_UNSUPPORTED",
        decision_outcome="UNSUPPORTED_REASONING",
    )
    registry = SafetyPolicyRegistry((item,))
    assert registry.eligible_policies(**eligible_arguments()) == ()
    assert len(
        registry.eligible_policies(
            **eligible_arguments(requested_operations=("RECOMMEND_PRODUCT",))
        )
    ) == 1


def test_registry_does_not_execute_or_evaluate_policies():
    item = policy()
    registry = SafetyPolicyRegistry((item,))
    assert not hasattr(item, "execute")
    assert not hasattr(registry, "evaluate")
    assert not hasattr(registry, "execute")
