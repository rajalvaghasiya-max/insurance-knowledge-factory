import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (
    REPOSITORY_ROOT
    / "knowledge_domains"
    / "health"
    / "field_registry"
    / "health_field_registry.json"
)

EXPECTED_FIELD_IDS = {
    "copay",
    "room_rent",
    "ped_waiting_period",
    "specific_disease_waiting_period",
    "restoration_benefit",
    "initial_waiting_period",
    "currency_sub_limit",
    "currency_deductible_option",
    "currency_sum_insured_threshold",
}

ALLOWED_MATURITY = {
    "extractor_supported",
    "limited_candidate",
    "router_supported",
    "evidence_discoverable",
}


def load_registry() -> dict:
    with REGISTRY_PATH.open(encoding="utf-8") as registry_file:
        return json.load(registry_file)


def test_health_field_registry_has_expected_canonical_fields() -> None:
    registry = load_registry()

    field_ids = {field["field_id"] for field in registry["fields"]}

    assert registry["schema_version"] == "0.2"
    assert field_ids == EXPECTED_FIELD_IDS


def test_health_field_registry_has_unique_operational_field_ids() -> None:
    registry = load_registry()

    operational_ids = [
        operational_id
        for field in registry["fields"]
        for operational_id in field["operational_field_ids"]
    ]

    assert len(operational_ids) == len(set(operational_ids))


def test_room_rent_preserves_legacy_operational_field_id() -> None:
    registry = load_registry()

    room_rent = next(
        field
        for field in registry["fields"]
        if field["field_id"] == "room_rent"
    )

    assert room_rent["operational_field_ids"] == ["room_rent_limit"]
    assert room_rent["maturity"] == "extractor_supported"


def test_every_field_has_a_valid_maturity_and_evidence_contract() -> None:
    registry = load_registry()

    for field in registry["fields"]:
        assert field["maturity"] in ALLOWED_MATURITY
        assert field["evidence_expectations"]["preferred_source_types"]
        assert field["notes"]

def test_ped_waiting_period_is_extractor_supported() -> None:
    registry = load_registry()

    ped_waiting_period = next(
        field
        for field in registry["fields"]
        if field["field_id"] == "ped_waiting_period"
    )

    assert ped_waiting_period["maturity"] == "extractor_supported"
    assert ped_waiting_period["production_readiness"] == "production_candidate"
    assert (
        ped_waiting_period["evidence_expectations"][
            "requires_entity_scope_guard"
        ]
        is True
    )

def test_initial_waiting_period_is_extractor_supported() -> None:
    registry = load_registry()

    initial_waiting_period = next(
        field
        for field in registry["fields"]
        if field["field_id"] == "initial_waiting_period"
    )

    assert initial_waiting_period["maturity"] == "extractor_supported"
    assert initial_waiting_period["production_readiness"] == "production_candidate"
    assert initial_waiting_period["evidence_expectations"][
        "requires_entity_scope_guard"
    ] is True

