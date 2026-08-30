from __future__ import annotations

from capability_control.catalog import load_catalog, validate_catalog
from capability_control.development_protocol import (
    CapabilityImpactDeclaration,
    ChangedPath,
    evaluate_development_protocol,
)
from capability_control.scanner import CapabilityDriftReport, scan_repository


def _strict_catalog(*, ownership_paths: list[str]):
    return validate_catalog(
        {
            "catalog_version": "1.0",
            "enforcement_mode": "STRICT",
            "governed_roots": ["insurance_intelligence"],
            "capabilities": [
                {
                    "capability_id": "II.TEST.STRICT_BOUNDARY",
                    "name": "Strict boundary test capability",
                    "responsibility": "Own the bounded test implementation path.",
                    "plane": "INSURANCE_INTELLIGENCE_TEST",
                    "lifecycle_status": "ACTIVE",
                    "authority_role": "Test-only authority.",
                    "safety_invariants": ["Unknown governed code must fail closed."],
                    "reuse_policy": "REUSE",
                    "ownership_paths": ownership_paths,
                    "introduced_by": "TEST",
                    "supersedes": [],
                    "superseded_by": None,
                }
            ],
        }
    )


def test_current_repository_is_strict_and_fully_reconciled():
    catalog = load_catalog("governance/capabilities/catalog.json")
    report = scan_repository(repo_root=".", catalog=catalog)

    assert catalog.enforcement_mode == "STRICT"
    assert report.unclaimed_governed_files == ()
    assert report.stale_ownership_paths == ()
    assert report.missing_ownership_paths == ()
    assert report.missing_governed_roots == ()
    assert report.passes_enforcement is True


def test_strict_rejects_new_unclaimed_recommendation_bypass(tmp_path):
    root = tmp_path / "insurance_intelligence"
    root.mkdir()
    (root / "owned.py").write_text("VALUE = 1\n", encoding="utf-8")
    bypass = root / "recommendation_bypass.py"
    bypass.write_text("def recommend(): return 'winner'\n", encoding="utf-8")

    report = scan_repository(
        repo_root=tmp_path,
        catalog=_strict_catalog(ownership_paths=["insurance_intelligence/owned.py"]),
    )

    assert report.unclaimed_governed_files == (
        "insurance_intelligence/recommendation_bypass.py",
    )
    assert "UNCLAIMED_GOVERNED_FILE" in report.strict_failure_reasons
    assert report.passes_enforcement is False


def test_strict_rejects_deleted_owned_implementation(tmp_path):
    root = tmp_path / "insurance_intelligence"
    root.mkdir()

    report = scan_repository(
        repo_root=tmp_path,
        catalog=_strict_catalog(ownership_paths=["insurance_intelligence/deleted.py"]),
    )

    assert report.missing_ownership_paths == ("insurance_intelligence/deleted.py",)
    assert "MISSING_OWNERSHIP_PATH" in report.strict_failure_reasons
    assert report.passes_enforcement is False


def test_strict_rejects_stale_owned_directory(tmp_path):
    root = tmp_path / "insurance_intelligence"
    owned = root / "owned"
    owned.mkdir(parents=True)
    (owned / "README.txt").write_text("no governed python remains\n", encoding="utf-8")

    report = scan_repository(
        repo_root=tmp_path,
        catalog=_strict_catalog(ownership_paths=["insurance_intelligence/owned"]),
    )

    assert report.stale_ownership_paths == ("insurance_intelligence/owned",)
    assert "STALE_OWNERSHIP_PATH" in report.strict_failure_reasons
    assert report.passes_enforcement is False


def test_development_protocol_rejects_declared_but_unclaimed_recommendation_path():
    path = "insurance_intelligence/recommendation_bypass.py"
    record = _strict_catalog(ownership_paths=["insurance_intelligence/owned.py"]).capabilities[0]
    catalog = validate_catalog(
        {
            "catalog_version": "1.0",
            "enforcement_mode": "STRICT",
            "governed_roots": ["insurance_intelligence"],
            "capabilities": [
                {
                    "capability_id": record.capability_id,
                    "name": record.name,
                    "responsibility": record.responsibility,
                    "plane": record.plane,
                    "lifecycle_status": record.lifecycle_status,
                    "authority_role": record.authority_role,
                    "safety_invariants": list(record.safety_invariants),
                    "reuse_policy": record.reuse_policy,
                    "ownership_paths": list(record.ownership_paths),
                    "introduced_by": record.introduced_by,
                    "supersedes": list(record.supersedes),
                    "superseded_by": record.superseded_by,
                }
            ],
        }
    )
    scanner_report = CapabilityDriftReport(
        missing_governed_roots=(),
        missing_ownership_paths=(),
        unclaimed_governed_files=(path,),
        stale_ownership_paths=(),
        strict_failure_reasons=("UNCLAIMED_GOVERNED_FILE",),
    )
    fingerprints = {
        "capabilities": [
            {
                "capability_id": record.capability_id,
                "owned_module_paths": ["insurance_intelligence/owned.py"],
                "structural_fingerprint": "a" * 64,
            }
        ]
    }
    declaration = CapabilityImpactDeclaration(
        change_id="strict-bypass-test",
        classification="EXTEND",
        capability_ids=(record.capability_id,),
        rationale="",
        supersession_impact="NONE",
        authority_impact="No authority change.",
    )

    report = evaluate_development_protocol(
        changes=(
            ChangedPath("A", path),
            ChangedPath(
                "A",
                "governance/capabilities/impacts/strict-bypass-test.json",
            ),
        ),
        base_catalog=catalog,
        current_catalog=catalog,
        scanner_report=scanner_report,
        base_fingerprints=fingerprints,
        current_fingerprints=fingerprints,
        declaration=declaration,
    )

    assert f"UNCLAIMED_GOVERNED_CODE_REQUIRES_NEW_REVIEW {path}" in report.errors
