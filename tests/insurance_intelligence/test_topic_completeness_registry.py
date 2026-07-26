from __future__ import annotations

import pytest

from insurance_intelligence.contracts.topic_completeness import (
    build_component_definition,
    build_topic_definition,
)
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
    TopicCompletenessRegistryError,
)


def _definition(
    topic_id: str,
    topic_version: str,
    *,
    domain: str = "health",
):
    component = build_component_definition(
        component_id="core_fact",
        requirement_type="CORE_FACT_REQUIREMENT",
        required=True,
        acceptable_requirement_statuses=("SATISFIED",),
        acceptable_evidence_roles=("SUPPORTING",),
        minimum_authority="AUTHORITATIVE",
        reason="Resolve the governed core fact.",
    )
    return build_topic_definition(
        topic_id=topic_id,
        topic_version=topic_version,
        domain=domain,
        components=(component,),
    )


def test_registers_and_gets_exact_topic_version():
    definition = _definition("conditional_obligation", "1.0")
    registry = TopicCompletenessRegistry((definition,))

    assert registry.get("conditional_obligation", "1.0") == definition
    assert registry.contains(
        topic_id="conditional_obligation",
        topic_version="1.0",
    )


def test_rejects_non_definition_registration():
    registry = TopicCompletenessRegistry()

    with pytest.raises(
        TopicCompletenessRegistryError,
        match="must be a TopicDefinition",
    ):
        registry.register(object())  # type: ignore[arg-type]


def test_rejects_duplicate_topic_version_registration():
    definition = _definition("conditional_obligation", "1.0")
    registry = TopicCompletenessRegistry((definition,))

    with pytest.raises(
        TopicCompletenessRegistryError,
        match="duplicate topic registration",
    ):
        registry.register(definition)


def test_single_registered_version_supports_unversioned_lookup():
    definition = _definition("room_eligibility", "1.0")
    registry = TopicCompletenessRegistry((definition,))

    assert registry.get("room_eligibility") == definition


def test_multiple_versions_require_active_version_for_unversioned_lookup():
    registry = TopicCompletenessRegistry(
        (
            _definition("room_eligibility", "1.0"),
            _definition("room_eligibility", "2.0"),
        )
    )

    with pytest.raises(
        TopicCompletenessRegistryError,
        match="ambiguous without an active version",
    ):
        registry.get("room_eligibility")


def test_active_version_resolves_unversioned_lookup():
    first = _definition("room_eligibility", "1.0")
    second = _definition("room_eligibility", "2.0")
    registry = TopicCompletenessRegistry((first, second))

    registry.set_active_version(
        topic_id="room_eligibility",
        topic_version="2.0",
    )

    assert registry.get("room_eligibility") == second
    assert registry.active_version("room_eligibility") == "2.0"


def test_register_can_mark_definition_active():
    definition = _definition("waiting_period", "1.0")
    registry = TopicCompletenessRegistry()

    registry.register(definition, active=True)

    assert registry.get("waiting_period") == definition


def test_cannot_activate_unregistered_version():
    registry = TopicCompletenessRegistry()

    with pytest.raises(
        TopicCompletenessRegistryError,
        match="cannot activate unregistered topic",
    ):
        registry.set_active_version(
            topic_id="conditional_obligation",
            topic_version="1.0",
        )


def test_unknown_exact_topic_version_is_rejected():
    registry = TopicCompletenessRegistry()

    with pytest.raises(
        TopicCompletenessRegistryError,
        match="topic not registered",
    ):
        registry.get("conditional_obligation", "1.0")


def test_unknown_unversioned_topic_is_rejected():
    registry = TopicCompletenessRegistry()

    with pytest.raises(
        TopicCompletenessRegistryError,
        match="topic not registered",
    ):
        registry.get("conditional_obligation")


def test_all_definitions_are_deterministically_ordered():
    motor = _definition("deductible", "1.0", domain="motor")
    health_v2 = _definition("copayment", "2.0")
    health_v1 = _definition("copayment", "1.0")
    registry = TopicCompletenessRegistry((motor, health_v2, health_v1))

    assert registry.all_definitions() == (health_v1, health_v2, motor)


def test_by_domain_filters_without_product_or_insurer_logic():
    health = _definition("conditional_obligation", "1.0", domain="health")
    motor = _definition("deductible", "1.0", domain="motor")
    registry = TopicCompletenessRegistry((motor, health))

    assert registry.by_domain("health") == (health,)
    assert registry.by_domain("motor") == (motor,)


def test_by_domain_rejects_invalid_domain():
    registry = TopicCompletenessRegistry()

    with pytest.raises(
        TopicCompletenessRegistryError,
        match="domain must be one of",
    ):
        registry.by_domain("property")


def test_versions_are_sorted_and_empty_for_unknown_topic():
    registry = TopicCompletenessRegistry(
        (
            _definition("copayment", "2.0"),
            _definition("copayment", "1.0"),
        )
    )

    assert registry.versions("copayment") == ("1.0", "2.0")
    assert registry.versions("unknown") == ()


def test_returned_collections_do_not_expose_internal_mutability():
    definition = _definition("conditional_obligation", "1.0")
    registry = TopicCompletenessRegistry((definition,))

    snapshot = registry.all_definitions()
    assert isinstance(snapshot, tuple)
    assert snapshot == (definition,)

    with pytest.raises(AttributeError):
        snapshot.append(definition)  # type: ignore[attr-defined]
