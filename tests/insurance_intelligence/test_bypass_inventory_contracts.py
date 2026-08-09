from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.bypass_inventory import (
    STAR_COMPREHENSIVE_PILOT_ID,
    build_default_bypass_inventory,
)
from insurance_intelligence.contracts.bypass_inventory import (
    BypassDisposition,
    BypassInventoryError,
    BypassInventoryEntry,
    BypassPathKind,
    BypassReachability,
    build_inventory,
)


def test_default_inventory_is_versioned_and_deterministic():
    first = build_default_bypass_inventory()
    second = build_default_bypass_inventory()
    assert first == second
    assert first.schema_version == "1.0"
    assert first.inventory_version == "1.0.0"
    assert len(first.entries) == 8


def test_inventory_contains_unique_paths_and_ids():
    inventory = build_default_bypass_inventory()
    assert len({item.path_id for item in inventory.entries}) == len(inventory.entries)
    assert len({item.repository_path for item in inventory.entries}) == len(inventory.entries)


def test_explicitly_deferred_paths_are_not_active_ungoverned():
    inventory = build_default_bypass_inventory()
    deferred = [
        item for item in inventory.entries
        if item.disposition is BypassDisposition.EXPLICITLY_DEFERRED
    ]
    assert deferred
    assert all(
        item.reachability is not BypassReachability.ACTIVE_UNGOVERNED
        for item in deferred
    )


def test_star_pilot_has_no_unsafe_reachable_entry():
    inventory = build_default_bypass_inventory()
    assert inventory.unsafe_reachable_entries(STAR_COMPREHENSIVE_PILOT_ID) == ()


def test_inventory_records_static_artifacts_separately_from_executable_paths():
    inventory = build_default_bypass_inventory()
    static = [item for item in inventory.entries if item.path_kind is BypassPathKind.STATIC_ARTIFACT]
    executable = [item for item in inventory.entries if item.path_kind is BypassPathKind.EXECUTABLE_UTILITY]
    assert len(static) == 3
    assert len(executable) == 3
    assert all(item.reachability is BypassReachability.STATIC_ARTIFACT_UNREACHABLE for item in static)
    assert all(item.reachability is BypassReachability.CERTIFIED_PILOT_UNREACHABLE for item in executable)


def test_inventory_is_immutable():
    inventory = build_default_bypass_inventory()
    with pytest.raises(FrozenInstanceError):
        inventory.inventory_version = "2.0.0"  # type: ignore[misc]


def test_active_ungoverned_entry_is_rejected():
    with pytest.raises(BypassInventoryError, match="active ungoverned"):
        BypassInventoryEntry(
            path_id="unsafe",
            repository_path="scripts/unsafe.py",
            path_kind=BypassPathKind.EXECUTABLE_UTILITY,
            recommendation_capable=True,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.ACTIVE_UNGOVERNED,
            certified_pilots=(STAR_COMPREHENSIVE_PILOT_ID,),
            evidence_refs=("scripts/unsafe.py",),
            rationale="unsafe",
        )


def test_duplicate_repository_paths_are_rejected():
    item = build_default_bypass_inventory().entries[0]
    with pytest.raises(BypassInventoryError, match="repository_path values must be unique"):
        build_inventory(
            inventory_id="x",
            inventory_version="1.0.0",
            entries=(item, item.__class__(**{**item.__dict__, "path_id": "other"})),
        )
