from __future__ import annotations

import json

import pytest

from capability_control.catalog import CapabilityCatalogError, load_catalog, validate_catalog


def _catalog(**overrides):
    raw = {
        "catalog_version": "1.0",
        "enforcement_mode": "RECONCILIATION",
        "governed_roots": ["capability_control"],
        "capabilities": [
            {
                "capability_id": "PLATFORM.CAPABILITY_CONTROL_PLANE",
                "name": "Control plane",
                "responsibility": "Govern repository capability memory.",
                "plane": "PLATFORM_GOVERNANCE",
                "lifecycle_status": "ACTIVE",
                "authority_role": "Architecture-memory integrity only.",
                "safety_invariants": ["Repository structure is independently reconciled."],
                "reuse_policy": "REUSE",
                "ownership_paths": ["capability_control"],
                "introduced_by": "BLOCKER-202",
                "supersedes": [],
                "superseded_by": None,
            }
        ],
    }
    raw.update(overrides)
    return raw


def test_current_catalog_loads():
    catalog = load_catalog("governance/capabilities/catalog.json")
    assert catalog.catalog_version == "1.0"
    assert catalog.enforcement_mode == "STRICT"
    assert catalog.capabilities[0].capability_id == "PLATFORM.CAPABILITY_CONTROL_PLANE"


def test_catalog_rejects_roadmap_field():
    raw = _catalog()
    raw["capabilities"][0]["allowed_next_action"] = "BUILD_MORE"
    with pytest.raises(CapabilityCatalogError, match="unsupported keys"):
        validate_catalog(raw)


def test_catalog_rejects_duplicate_capability_id():
    raw = _catalog()
    raw["capabilities"].append(dict(raw["capabilities"][0]))
    with pytest.raises(CapabilityCatalogError, match="must be unique"):
        validate_catalog(raw)


def test_catalog_rejects_duplicate_ownership_path():
    raw = _catalog()
    second = dict(raw["capabilities"][0])
    second["capability_id"] = "PLATFORM.SECOND_CONTROL"
    raw["capabilities"].append(second)
    with pytest.raises(CapabilityCatalogError, match="claimed by both"):
        validate_catalog(raw)


def test_catalog_rejects_unknown_supersession_target():
    raw = _catalog()
    raw["capabilities"][0]["supersedes"] = ["PLATFORM.DOES_NOT_EXIST"]
    with pytest.raises(CapabilityCatalogError, match="supersedes unknown capability"):
        validate_catalog(raw)


def test_catalog_requires_bidirectional_supersession_lineage():
    raw = _catalog()
    old = dict(raw["capabilities"][0])
    old.update(
        {
            "capability_id": "PLATFORM.OLD_CONTROL",
            "lifecycle_status": "SUPERSEDED",
            "ownership_paths": ["legacy_control"],
            "superseded_by": "PLATFORM.CAPABILITY_CONTROL_PLANE",
        }
    )
    raw["capabilities"].append(old)
    with pytest.raises(CapabilityCatalogError, match="must be bidirectional"):
        validate_catalog(raw)


def test_catalog_load_rejects_invalid_json(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(CapabilityCatalogError, match="cannot load capability catalog"):
        load_catalog(path)


def test_catalog_load_merges_sorted_fragment_files(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(_catalog()), encoding="utf-8")
    fragment_dir = tmp_path / "catalog.d"
    fragment_dir.mkdir()
    fragment_dir.joinpath("b.json").write_text(
        json.dumps(
            {
                "capabilities": [
                    {
                        "capability_id": "PLATFORM.FRAGMENT_B",
                        "name": "Fragment B",
                        "responsibility": "Second fragment capability.",
                        "plane": "PLATFORM_GOVERNANCE",
                        "lifecycle_status": "ACTIVE",
                        "authority_role": "Test fragment only.",
                        "safety_invariants": ["Fragments must merge before validation."],
                        "reuse_policy": "REUSE",
                        "ownership_paths": ["fragment_b"],
                        "introduced_by": "TEST",
                        "supersedes": [],
                        "superseded_by": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    fragment_dir.joinpath("a.json").write_text(
        json.dumps(
            {
                "capabilities": [
                    {
                        "capability_id": "PLATFORM.FRAGMENT_A",
                        "name": "Fragment A",
                        "responsibility": "First fragment capability.",
                        "plane": "PLATFORM_GOVERNANCE",
                        "lifecycle_status": "ACTIVE",
                        "authority_role": "Test fragment only.",
                        "safety_invariants": ["Fragment loading is deterministic."],
                        "reuse_policy": "REUSE",
                        "ownership_paths": ["fragment_a"],
                        "introduced_by": "TEST",
                        "supersedes": [],
                        "superseded_by": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    catalog = load_catalog(path)

    assert tuple(record.capability_id for record in catalog.capabilities[-2:]) == (
        "PLATFORM.FRAGMENT_A",
        "PLATFORM.FRAGMENT_B",
    )


def test_catalog_fragment_rejects_non_capability_payload(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(_catalog()), encoding="utf-8")
    fragment_dir = tmp_path / "catalog.d"
    fragment_dir.mkdir()
    fragment_dir.joinpath("bad.json").write_text(
        json.dumps({"capabilities": [], "roadmap": "NO"}), encoding="utf-8"
    )

    with pytest.raises(CapabilityCatalogError, match="must contain only a capabilities list"):
        load_catalog(path)
