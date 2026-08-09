from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.terminology.catalogue import (
    COPAYMENT_CONCEPT,
    DEDUCTIBLE_CONCEPT,
    INITIAL_CANONICAL_CONCEPTS,
    RESTORATION_BENEFIT_CONCEPT,
    build_initial_canonical_catalogue_snapshot,
)


def test_initial_catalogue_contains_exactly_three_controlled_concepts() -> None:
    assert INITIAL_CANONICAL_CONCEPTS == (
        COPAYMENT_CONCEPT,
        DEDUCTIBLE_CONCEPT,
        RESTORATION_BENEFIT_CONCEPT,
    )


def test_initial_catalogue_has_stable_unique_identifiers() -> None:
    assert {item.concept_family_id for item in INITIAL_CANONICAL_CONCEPTS} == {
        "health:cost_sharing:copayment",
        "health:cost_sharing:deductible",
        "health:coverage_capacity:restoration_benefit",
    }


def test_initial_catalogue_is_health_domain_only() -> None:
    assert {item.domain for item in INITIAL_CANONICAL_CONCEPTS} == {"health"}


def test_cost_sharing_concepts_share_subtype_but_not_identity() -> None:
    assert COPAYMENT_CONCEPT.concept_subtype == "cost_sharing"
    assert DEDUCTIBLE_CONCEPT.concept_subtype == "cost_sharing"
    assert COPAYMENT_CONCEPT.concept_family_id != DEDUCTIBLE_CONCEPT.concept_family_id
    assert COPAYMENT_CONCEPT.definition != DEDUCTIBLE_CONCEPT.definition


def test_restoration_is_not_modelled_as_cost_sharing() -> None:
    assert RESTORATION_BENEFIT_CONCEPT.concept_subtype == "coverage_capacity"
    assert RESTORATION_BENEFIT_CONCEPT.concept_family_id.startswith(
        "health:coverage_capacity:"
    )


def test_definitions_preserve_policy_specific_variability() -> None:
    assert "specified proportion" in COPAYMENT_CONCEPT.definition
    assert "basis and period" in DEDUCTIBLE_CONCEPT.definition
    assert "product-specific conditions" in RESTORATION_BENEFIT_CONCEPT.definition


def test_concepts_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        COPAYMENT_CONCEPT.canonical_name = "Changed"  # type: ignore[misc]


def test_catalogue_snapshot_is_concept_only() -> None:
    snapshot = build_initial_canonical_catalogue_snapshot()
    assert snapshot.concepts == INITIAL_CANONICAL_CONCEPTS
    assert snapshot.marketing_terms == ()
    assert snapshot.implementations == ()
    assert snapshot.alias_candidates == ()


def test_catalogue_snapshot_id_is_stable() -> None:
    first = build_initial_canonical_catalogue_snapshot()
    second = build_initial_canonical_catalogue_snapshot()
    assert first.snapshot_id == second.snapshot_id


def test_catalogue_snapshot_builds_fail_closed_empty_resolver() -> None:
    resolver = build_initial_canonical_catalogue_snapshot().build_resolver()
    assert resolver.concepts == INITIAL_CANONICAL_CONCEPTS
    assert resolver.marketing_terms == ()
    assert resolver.implementations == ()
    assert resolver.alias_candidates == ()
