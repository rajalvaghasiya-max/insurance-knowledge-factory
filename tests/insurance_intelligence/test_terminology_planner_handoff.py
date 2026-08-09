from insurance_intelligence.contracts.terminology import CanonicalConceptFamily
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
)
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1
from insurance_intelligence.terminology.planner_handoff import build_planner_handoff


def test_resolved_health_concept_becomes_planning_hint() -> None:
    resolution = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "co pay", domain="health"
    )
    handoff = build_planner_handoff(resolution)

    assert handoff.status == "READY"
    assert handoff.concept_id == "health:concept:copayment"
    assert handoff.domain == "health"
    assert handoff.downstream_topic == "conditional_copayment"
    assert handoff.candidate_concept_ids == ("health:concept:copayment",)


def test_ready_handoff_does_not_claim_downstream_capability_exists() -> None:
    resolution = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "deductible", domain="health"
    )
    handoff = build_planner_handoff(resolution)

    assert handoff.status == "READY"
    assert handoff.downstream_topic == "deductible"
    assert handoff.reason_codes == ("CANONICAL_CONCEPT_READY_FOR_PLANNING",)
    assert not hasattr(handoff, "rule_id")
    assert not hasattr(handoff, "evidence_ids")
    assert not hasattr(handoff, "finding")
    assert not hasattr(handoff, "applicability")


def test_ambiguous_terminology_blocks_planner_target() -> None:
    resolution = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "amount I pay myself", domain="health"
    )
    handoff = build_planner_handoff(resolution)

    assert resolution.status == "AMBIGUOUS"
    assert handoff.status == "BLOCKED"
    assert handoff.concept_id is None
    assert handoff.downstream_topic is None
    assert set(handoff.candidate_concept_ids) == {
        "health:concept:copayment",
        "health:concept:deductible",
    }
    assert handoff.reason_codes == ("TERMINOLOGY_AMBIGUOUS",)


def test_unresolved_terminology_blocks_handoff_without_guessing() -> None:
    resolution = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "mystery insurance feature", domain="health"
    )
    handoff = build_planner_handoff(resolution)

    assert resolution.status == "NOT_RESOLVED"
    assert handoff.status == "BLOCKED"
    assert handoff.candidate_concept_ids == ()
    assert handoff.reason_codes == ("TERMINOLOGY_NOT_RESOLVED",)


def test_invalid_resolution_input_fails_closed() -> None:
    handoff = build_planner_handoff(object())

    assert handoff.status == "INVALID_INPUT"
    assert handoff.concept_id is None
    assert handoff.downstream_topic is None
    assert handoff.reason_codes == ("INVALID_TERMINOLOGY_RESOLUTION",)


def test_resolved_concept_without_downstream_topic_is_blocked() -> None:
    registry = CanonicalConceptRegistry(
        (
            CanonicalConceptDefinition(
                concept=CanonicalConceptFamily(
                    concept_family_id="health:concept:unrouted",
                    canonical_name="Unrouted concept",
                    definition="A governed concept intentionally lacking planner routing.",
                    domain="health",
                ),
                concept_type="GENERAL_TERM",
                aliases=("unrouted",),
                downstream_topic=None,
            ),
        )
    )
    resolution = CanonicalConceptResolver(registry).resolve("unrouted", domain="health")
    handoff = build_planner_handoff(resolution)

    assert resolution.status == "RESOLVED"
    assert handoff.status == "BLOCKED"
    assert handoff.concept_id is None
    assert handoff.downstream_topic is None
    assert handoff.candidate_concept_ids == ("health:concept:unrouted",)
    assert handoff.reason_codes == ("MISSING_DOWNSTREAM_TOPIC",)


def test_handoff_is_deterministic() -> None:
    resolver = CanonicalConceptResolver(build_health_concept_registry_v1())
    resolution = resolver.resolve("room category limit", domain="health")

    assert build_planner_handoff(resolution) == build_planner_handoff(resolution)
