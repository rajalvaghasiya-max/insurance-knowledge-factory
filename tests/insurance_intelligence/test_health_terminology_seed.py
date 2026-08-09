from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import (
    HEALTH_CONCEPTS_V1,
    build_health_concept_registry_v1,
)


def test_health_seed_has_unique_stable_concept_ids():
    ids = tuple(item.concept_id for item in HEALTH_CONCEPTS_V1)
    assert len(ids) == 12
    assert len(ids) == len(set(ids))
    assert all(item.domain == "health" for item in HEALTH_CONCEPTS_V1)


def test_high_value_health_concepts_are_seeded():
    ids = {item.concept_id for item in HEALTH_CONCEPTS_V1}
    assert {
        "health:concept:copayment",
        "health:concept:deductible",
        "health:concept:room_rent_limit",
        "health:concept:waiting_period",
        "health:concept:pre_existing_disease",
        "health:concept:restoration",
        "health:concept:sum_insured",
        "health:concept:sub_limit",
        "health:concept:exclusion",
        "health:concept:network_hospital",
        "health:concept:cashless_claim",
        "health:concept:reimbursement_claim",
    } <= ids


def test_seed_builds_without_ungoverned_phrase_collisions():
    registry = build_health_concept_registry_v1()
    assert len(registry.all_concepts()) == 12


def test_copay_alias_resolves_to_canonical_concept():
    result = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "CO PAY", domain="health"
    )
    assert result.status == "RESOLVED"
    assert result.selected_concept is not None
    assert result.selected_concept.concept_id == "health:concept:copayment"
    assert result.selected_concept.downstream_topic == "conditional_copayment"


def test_room_category_customer_language_resolves():
    result = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "which room can I take", domain="health"
    )
    assert result.status == "RESOLVED"
    assert result.selected_concept is not None
    assert result.selected_concept.concept_id == "health:concept:room_rent_limit"


def test_ped_alias_resolves():
    result = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "PED", domain="health"
    )
    assert result.status == "RESOLVED"
    assert result.selected_concept is not None
    assert result.selected_concept.concept_id == "health:concept:pre_existing_disease"


def test_restoration_customer_phrase_resolves():
    result = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "does my cover come back after a claim", domain="health"
    )
    assert result.status == "RESOLVED"
    assert result.selected_concept is not None
    assert result.selected_concept.concept_id == "health:concept:restoration"


def test_vague_out_of_pocket_phrase_is_ambiguous_not_guessed():
    result = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "amount I pay myself", domain="health"
    )
    assert result.status == "AMBIGUOUS"
    assert result.selected_concept is None
    assert {item.concept_id for item in result.candidates} == {
        "health:concept:copayment",
        "health:concept:deductible",
    }


def test_unknown_phrase_remains_not_resolved():
    result = CanonicalConceptResolver(build_health_concept_registry_v1()).resolve(
        "mystery wellness multiplier", domain="health"
    )
    assert result.status == "NOT_RESOLVED"
    assert result.selected_concept is None


def test_seed_entries_route_language_only_not_product_applicability():
    for item in HEALTH_CONCEPTS_V1:
        assert item.downstream_topic
        assert not hasattr(item, "product_id")
        assert not hasattr(item, "insurer_id")
        assert not hasattr(item, "applicability_status")
