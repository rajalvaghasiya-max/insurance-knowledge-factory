from dataclasses import fields

import pytest

from insurance_intelligence.contracts.terminology import CanonicalConceptFamily
from insurance_intelligence.reasoning.registry import RuleRegistryError
from insurance_intelligence.reasoning.rules import default_rule_registry
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
    CanonicalConceptRegistryError,
)
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1
from insurance_intelligence.terminology.planner_handoff import (
    TerminologyPlannerHandoff,
    build_planner_handoff,
)


def _concept(
    concept_id: str,
    *,
    name: str,
    domain: str,
    alias: str,
    ambiguity_group: str | None = None,
    downstream_topic: str = "documented_fact",
) -> CanonicalConceptDefinition:
    return CanonicalConceptDefinition(
        concept=CanonicalConceptFamily(
            concept_family_id=concept_id,
            canonical_name=name,
            definition=f"Governed definition for {name}.",
            domain=domain,
        ),
        concept_type="GENERAL_TERM",
        aliases=(alias,),
        ambiguity_group=ambiguity_group,
        downstream_topic=downstream_topic,
    )


def test_same_domain_alias_collision_requires_explicit_governed_ambiguity() -> None:
    first = _concept(
        "health:concept:first",
        name="First",
        domain="health",
        alias="shared phrase",
    )
    second = _concept(
        "health:concept:second",
        name="Second",
        domain="health",
        alias="shared phrase",
    )

    with pytest.raises(CanonicalConceptRegistryError, match="ambiguity_group"):
        CanonicalConceptRegistry((first, second))


def test_cross_domain_phrase_is_ambiguous_without_domain_and_resolves_with_domain() -> None:
    health = _concept(
        "health:concept:cover_amount",
        name="Health cover amount",
        domain="health",
        alias="cover amount",
    )
    life = _concept(
        "life:concept:cover_amount",
        name="Life cover amount",
        domain="life",
        alias="cover amount",
    )
    resolver = CanonicalConceptResolver(CanonicalConceptRegistry((health, life)))

    unresolved_domain = resolver.resolve("cover amount")
    assert unresolved_domain.status == "AMBIGUOUS"
    assert unresolved_domain.selected_concept is None
    assert {item.concept_id for item in unresolved_domain.candidates} == {
        health.concept_id,
        life.concept_id,
    }

    health_only = resolver.resolve("cover amount", domain="health")
    assert health_only.status == "RESOLVED"
    assert health_only.selected_concept == health


def test_ready_handoff_cannot_publish_product_entity_or_evidence_identity() -> None:
    resolution = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "copay",
        domain="health",
    )
    handoff = build_planner_handoff(resolution)

    assert handoff.status == "READY"
    field_names = {item.name for item in fields(TerminologyPlannerHandoff)}
    assert field_names.isdisjoint(
        {
            "insurer_id",
            "product_id",
            "product_variant_id",
            "entity_id",
            "evidence_id",
            "evidence_ids",
            "document_id",
            "finding_id",
            "rule_id",
        }
    )


def test_ready_terminology_handoff_does_not_imply_reasoning_capability() -> None:
    resolution = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "deductible",
        domain="health",
    )
    handoff = build_planner_handoff(resolution)

    assert handoff.status == "READY"
    assert handoff.downstream_topic == "deductible"

    registry = default_rule_registry()
    with pytest.raises(RuleRegistryError, match="topic"):
        registry.eligible_rules(
            domain="health",
            topic=handoff.downstream_topic,
            requirement_type="EXPLAIN",
            available_evidence_topics=(handoff.downstream_topic,),
            available_evidence_roles=("SUPPORTING",),
            available_authorities=("ANY_GOVERNED",),
        )


def test_ambiguous_terminology_cannot_publish_planner_target() -> None:
    resolution = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "amount I pay myself",
        domain="health",
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
