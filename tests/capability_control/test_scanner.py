from __future__ import annotations

from capability_control.catalog import validate_catalog
from capability_control.scanner import scan_repository


def _catalog(*, mode="RECONCILIATION", governed_roots=None, ownership_paths=None):
    return validate_catalog(
        {
            "catalog_version": "1.0",
            "enforcement_mode": mode,
            "governed_roots": governed_roots or ["governed"],
            "capabilities": [
                {
                    "capability_id": "PLATFORM.TEST_CONTROL",
                    "name": "Test control",
                    "responsibility": "Test repository reconciliation.",
                    "plane": "PLATFORM_GOVERNANCE",
                    "lifecycle_status": "ACTIVE",
                    "authority_role": "Test-only ownership authority.",
                    "safety_invariants": ["Unregistered strict-mode code must fail."],
                    "reuse_policy": "REUSE",
                    "ownership_paths": ownership_paths or ["governed/owned.py"],
                    "introduced_by": "TEST",
                    "supersedes": [],
                    "superseded_by": None,
                }
            ],
        }
    )


def test_scanner_reports_but_does_not_fail_unclaimed_file_in_reconciliation_mode(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    (governed / "owned.py").write_text("VALUE = 1\n", encoding="utf-8")
    (governed / "unclaimed.py").write_text("VALUE = 2\n", encoding="utf-8")

    report = scan_repository(repo_root=tmp_path, catalog=_catalog())

    assert report.unclaimed_governed_files == ("governed/unclaimed.py",)
    assert report.structural_drift_detected is True
    assert report.passes_enforcement is True


def test_scanner_fails_unclaimed_file_in_strict_mode(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    (governed / "owned.py").write_text("VALUE = 1\n", encoding="utf-8")
    (governed / "unclaimed.py").write_text("VALUE = 2\n", encoding="utf-8")

    report = scan_repository(repo_root=tmp_path, catalog=_catalog(mode="STRICT"))

    assert report.unclaimed_governed_files == ("governed/unclaimed.py",)
    assert report.passes_enforcement is False
    assert "UNCLAIMED_GOVERNED_FILE" in report.strict_failure_reasons


def test_scanner_fails_when_catalog_claims_missing_path(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    (governed / "present.py").write_text("VALUE = 1\n", encoding="utf-8")
    catalog = _catalog(ownership_paths=["governed/missing.py"])

    report = scan_repository(repo_root=tmp_path, catalog=catalog)

    assert report.missing_ownership_paths == ("governed/missing.py",)
    assert report.passes_enforcement is False
    assert "MISSING_OWNERSHIP_PATH" in report.strict_failure_reasons


def test_scanner_fails_when_governed_root_disappears(tmp_path):
    catalog = _catalog(governed_roots=["missing_root"], ownership_paths=["also_missing.py"])

    report = scan_repository(repo_root=tmp_path, catalog=catalog)

    assert report.missing_governed_roots == ("missing_root",)
    assert report.passes_enforcement is False
    assert "MISSING_GOVERNED_ROOT" in report.strict_failure_reasons


def test_current_repository_control_plane_reconciles_its_own_files():
    from capability_control.catalog import load_catalog

    catalog = load_catalog("governance/capabilities/catalog.json")
    report = scan_repository(repo_root=".", catalog=catalog)

    assert report.missing_governed_roots == ()
    assert report.missing_ownership_paths == ()
    assert not any(
        path.startswith("capability_control/")
        for path in report.unclaimed_governed_files
    )
    assert report.passes_enforcement is True
