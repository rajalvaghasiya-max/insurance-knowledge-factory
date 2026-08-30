from __future__ import annotations

import pytest

from capability_control.catalog import validate_catalog
from capability_control.system_map import CapabilitySystemMapError, render_capability_map


def _catalog():
    return validate_catalog(
        {
            "catalog_version": "1.0",
            "enforcement_mode": "RECONCILIATION",
            "governed_roots": ["capability_control"],
            "capabilities": [
                {
                    "capability_id": "PLATFORM.TEST",
                    "name": "Test Capability",
                    "responsibility": "Provide a deterministic test responsibility.",
                    "plane": "PLATFORM_GOVERNANCE",
                    "lifecycle_status": "ACTIVE",
                    "authority_role": "Test-only descriptive authority.",
                    "safety_invariants": ["Never invent roadmap authority."],
                    "reuse_policy": "REUSE",
                    "ownership_paths": ["capability_control/test.py"],
                    "introduced_by": "TEST",
                    "supersedes": [],
                    "superseded_by": None,
                    "notes": "Fixture.",
                }
            ],
        }
    )


def _fingerprints():
    return {
        "PLATFORM.TEST": {
            "capability_id": "PLATFORM.TEST",
            "owned_module_paths": ["capability_control/test.py"],
            "structural_fingerprint": "a" * 64,
        }
    }


def test_render_capability_map_is_deterministic_compact_navigation_view() -> None:
    first = render_capability_map(_catalog(), _fingerprints(), fingerprint_schema_version="1.0")
    second = render_capability_map(_catalog(), _fingerprints(), fingerprint_schema_version="1.0")
    assert first == second
    assert "GENERATED — DO NOT EDIT" in first
    assert "PLATFORM.TEST" in first
    assert "Test-only descriptive authority." in first
    assert "Ownership boundary" in first
    assert "capability_control/test.py" in first
    assert "a" * 64 in first
    assert "deterministic test responsibility" not in first
    assert "Never invent roadmap authority." not in first
    assert "Detailed responsibility, safety invariants, notes and module-level structural evidence" in first
    assert "generated_at" not in first
    assert "commit_sha" not in first


def test_render_capability_map_fails_on_missing_fingerprint() -> None:
    with pytest.raises(CapabilitySystemMapError, match="capability mismatch"):
        render_capability_map(_catalog(), {}, fingerprint_schema_version="1.0")


def test_render_capability_map_fails_on_extra_fingerprint() -> None:
    fingerprints = _fingerprints()
    fingerprints["PLATFORM.EXTRA"] = {
        "capability_id": "PLATFORM.EXTRA",
        "owned_module_paths": [],
        "structural_fingerprint": "b" * 64,
    }
    with pytest.raises(CapabilitySystemMapError, match="capability mismatch"):
        render_capability_map(_catalog(), fingerprints, fingerprint_schema_version="1.0")


def test_render_capability_map_orders_planes_and_capabilities() -> None:
    raw = {
        "catalog_version": "1.0",
        "enforcement_mode": "RECONCILIATION",
        "governed_roots": ["capability_control"],
        "capabilities": [
            {
                "capability_id": "PLATFORM.Z",
                "name": "Zed",
                "responsibility": "Z responsibility.",
                "plane": "Z_PLANE",
                "lifecycle_status": "ACTIVE",
                "authority_role": "Z authority.",
                "safety_invariants": ["Z invariant."],
                "reuse_policy": "REUSE",
                "ownership_paths": ["capability_control/z.py"],
                "introduced_by": "TEST",
                "supersedes": [],
                "superseded_by": None,
                "notes": None,
            },
            {
                "capability_id": "PLATFORM.A",
                "name": "Aye",
                "responsibility": "A responsibility.",
                "plane": "A_PLANE",
                "lifecycle_status": "ACTIVE",
                "authority_role": "A authority.",
                "safety_invariants": ["A invariant."],
                "reuse_policy": "REUSE",
                "ownership_paths": ["capability_control/a.py"],
                "introduced_by": "TEST",
                "supersedes": [],
                "superseded_by": None,
                "notes": None,
            },
        ],
    }
    catalog = validate_catalog(raw)
    fingerprints = {
        "PLATFORM.Z": {"capability_id": "PLATFORM.Z", "owned_module_paths": ["capability_control/z.py"], "structural_fingerprint": "z" * 64},
        "PLATFORM.A": {"capability_id": "PLATFORM.A", "owned_module_paths": ["capability_control/a.py"], "structural_fingerprint": "a" * 64},
    }
    rendered = render_capability_map(catalog, fingerprints, fingerprint_schema_version="1.0")
    assert rendered.index("## A_PLANE") < rendered.index("## Z_PLANE")
