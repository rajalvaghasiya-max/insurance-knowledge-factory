"""Focused tests for the executable Star Health Comprehensive governed
foundation (MO-006B.1).

Star's identity and source hash are now CTO-approved. These tests
validate the five executable governed specifications directly against
the real, unmodified generic contracts and the real, unmodified
generic migration runner -- they do not duplicate contract
implementation logic. Only the two stages that require the archive
PDF (source registration build, classification build) are seeded with
schema-valid fixture data for the full-pipeline test, exactly as for
the equivalent Bajaj tests; identity and overlay always run for real
against the real specifications.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.run_governed_product_migration import (
    GovernedProductMigrationError,
    load_manifest,
    run_migration,
)
from factory_core.governance.product_identity_reference import (
    ProductIdentityReference,
    ProductIdentityReferenceError,
)

STAR_MANIFEST_PATH = "docs/architecture/star_health_star_comprehensive_migration_manifest.json"
STAR_IDENTITY_SPEC_PATH = "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
STAR_OVERLAY_SPEC_PATH = "docs/architecture/star_health_star_comprehensive_document_identity_resolution_spec.json"

APPROVED_ENTITY_ID = "star_health:star_comprehensive"
APPROVED_UIN = "SHAHLIP26044V092526"
APPROVED_SOURCE_PATH = "archive/raw_documents/star_health/star_comprehensive_policy_wording_2025.pdf"
APPROVED_SHA256 = "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --- 1-4: manifest and identity declare the exact approved values -------

def test_manifest_declares_approved_source_path():
    manifest = load_manifest(STAR_MANIFEST_PATH)
    assert manifest.expected_source_path == APPROVED_SOURCE_PATH


def test_manifest_declares_approved_sha256():
    manifest = load_manifest(STAR_MANIFEST_PATH)
    assert manifest.expected_source_sha256 == APPROVED_SHA256


def test_manifest_declares_approved_entity():
    manifest = load_manifest(STAR_MANIFEST_PATH)
    assert manifest.entity_id == APPROVED_ENTITY_ID
    assert manifest.insurer_id == "star_health"
    assert manifest.product_id == "star_comprehensive"


def test_identity_spec_declares_approved_uin():
    spec = _load(STAR_IDENTITY_SPEC_PATH)
    assert spec["product_identity"]["uin"] == APPROVED_UIN
    assert spec["product_identity"]["entity_id"] == APPROVED_ENTITY_ID


# --- 5-6: human review and executable identity contract validation ------

def test_identity_spec_is_human_reviewed():
    spec = _load(STAR_IDENTITY_SPEC_PATH)
    assert spec["reviewed_by_human"] is True
    assert spec["record_type"] == "product_identity_reference_v1"
    signal_types = {entry["signal_type"] for entry in spec["identity_evidence"]}
    assert "uin_exact_match" in signal_types
    assert "canonical_title_match" in signal_types
    assert any(entry["verification"] == "manual_reviewed" for entry in spec["identity_evidence"])


def test_identity_contract_validates_and_resolves():
    """Real, unmodified ProductIdentityReference contract -- not mocked."""
    result = ProductIdentityReference().build_from_spec_file(
        spec_path=STAR_IDENTITY_SPEC_PATH, repository_root="."
    )
    assert result.manifest["product_identity"]["entity_id"] == APPROVED_ENTITY_ID
    assert result.manifest["product_identity"]["uin"] == APPROVED_UIN
    assert result.manifest["identity_resolution_status"] == "resolved"


# --- 7-9: resolution/temporal/entitlement states -------------------------

def test_document_identity_resolution_spec_declares_resolved():
    spec = _load(STAR_OVERLAY_SPEC_PATH)
    assert spec["documents"][0]["resolution_status"] == "resolved"


def test_document_identity_resolution_spec_temporal_status_compatibility_unverified():
    spec = _load(STAR_OVERLAY_SPEC_PATH)
    assert spec["documents"][0]["temporal_status"] == "compatibility_unverified"


# --- 10: migration manifest validity -------------------------------------

def test_migration_manifest_loads_and_validates():
    manifest = load_manifest(STAR_MANIFEST_PATH)
    for key in ("generic_registration", "classification", "identity", "overlay"):
        assert manifest.specs[key].startswith("docs/architecture/star_health_star_comprehensive_")
    for key in ("bundle", "classification", "identity", "overlay"):
        assert manifest.outputs[key].startswith("knowledge/factory/")


# --- 11: no Star-specific runner -----------------------------------------

def test_no_star_specific_runner_script_exists():
    star_runners = list(Path("scripts").glob("run_star_*.py"))
    assert star_runners == [], f"unexpected Star-specific runner script(s): {star_runners}"


# --- 12/14: generic runner compatibility and missing-source fail-closed --

def test_generic_runner_executes_star_manifest_and_fails_closed_on_missing_source():
    """In this clean checkout the gitignored source PDF is absent. The
    real, unmodified generic runner (not a Star-specific one) must reach
    exactly this boundary and fail closed -- proving the manifest and
    all four specs are otherwise wired correctly."""
    with pytest.raises(GovernedProductMigrationError, match="source document was not found"):
        run_migration(".", STAR_MANIFEST_PATH)


# --- 13: source-hash mismatch fails closed when a runtime source exists --

def test_source_hash_mismatch_fails_closed_when_runtime_source_available(tmp_path):
    import shutil

    root = tmp_path
    for relative in (
        "docs/architecture/star_health_star_comprehensive_migration_manifest.json",
        "docs/architecture/star_health_star_comprehensive_generic_sources_registration_spec.json",
        "docs/architecture/star_health_star_comprehensive_document_classification_spec.json",
        "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json",
        "docs/architecture/star_health_star_comprehensive_document_identity_resolution_spec.json",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(relative), destination)

    wrong_source = root / APPROVED_SOURCE_PATH
    wrong_source.parent.mkdir(parents=True, exist_ok=True)
    wrong_source.write_bytes(b"this is not the approved Star policy wording")
    actual_hash = hashlib.sha256(b"this is not the approved Star policy wording").hexdigest()
    assert actual_hash != APPROVED_SHA256

    with pytest.raises(GovernedProductMigrationError, match="SHA-256 mismatch"):
        run_migration(root, root / "docs/architecture/star_health_star_comprehensive_migration_manifest.json")


# --- full-pipeline governed-state proof (mirrors the Bajaj pattern) ------

class _FakeSourceResult:
    bundle = {"registration_status": "generic_sources_registered_evidence_review_required"}


class _FakeClassificationResult:
    manifest = {"classification_status": "reviewed_document_classifications_recorded_not_published"}


_STAR_REGISTRATION_OUTPUT_RELATIVE = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/policy_wording_registration.json"
)
_STAR_CLASSIFICATION_OUTPUT_RELATIVE = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "governance/star_health_star_comprehensive_document_classification.json"
)


def _seed_star_registration_and_classification_fixtures(root):
    registration_path = root / _STAR_REGISTRATION_OUTPUT_RELATIVE
    registration_path.parent.mkdir(parents=True, exist_ok=True)
    registration_path.write_text(
        json.dumps(
            {
                "document": {
                    "document_id": "star_health_star_comprehensive_policy_wording_v1",
                    "document_version_id": APPROVED_SHA256,
                    "source_document_id": APPROVED_SHA256,
                    "document_type": "policy_wording",
                    "content_sha256": APPROVED_SHA256,
                }
            }
        ),
        encoding="utf-8",
    )
    classification_path = root / _STAR_CLASSIFICATION_OUTPUT_RELATIVE
    classification_path.parent.mkdir(parents=True, exist_ok=True)
    classification_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_version_id": APPROVED_SHA256,
                        "classification": "reusable_generic",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _prepare_star_shadow_repository_root(tmp_path):
    import shutil

    for relative in (
        STAR_MANIFEST_PATH,
        STAR_IDENTITY_SPEC_PATH,
        STAR_OVERLAY_SPEC_PATH,
        "docs/architecture/star_health_star_comprehensive_document_classification_spec.json",
        "docs/architecture/star_health_star_comprehensive_generic_sources_registration_spec.json",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(relative), destination)
    _seed_star_registration_and_classification_fixtures(tmp_path)
    return tmp_path


def test_full_pipeline_reproduces_expected_governed_states(tmp_path):
    """Real identity and overlay contracts, real Star specifications; only
    the two PDF-dependent stages are seeded, exactly as for Bajaj."""
    root = _prepare_star_shadow_repository_root(tmp_path)
    with patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.register_from_spec_file",
        return_value=_FakeSourceResult(),
    ), patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.write_outputs",
        return_value=root
        / "knowledge/factory/registry_backed/star_health_star_comprehensive/generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json",
    ), patch(
        "scripts.run_governed_product_migration.DocumentClassificationPolicy.classify_from_spec_file",
        return_value=_FakeClassificationResult(),
    ), patch(
        "scripts.run_governed_product_migration.DocumentClassificationPolicy.write_output",
        return_value=root / _STAR_CLASSIFICATION_OUTPUT_RELATIVE,
    ), patch(
        "scripts.run_governed_product_migration.require_expected_source",
        return_value=root / APPROVED_SOURCE_PATH,
    ):
        result = run_migration(root, STAR_MANIFEST_PATH)

    assert result["entity_id"] == APPROVED_ENTITY_ID
    assert result["source_registration_status"] == "generic_sources_registered_evidence_review_required"
    assert result["classification_status"] == "reviewed_document_classifications_recorded_not_published"
    assert result["identity_status"] == "resolved"
    assert result["resolution_status"] == "resolved"
    assert result["temporal_status"] == "compatibility_unverified"
    assert result["evidence_review_eligibility"] == "eligible_for_evidence_review"
    assert result["current_entitlement_publication_eligibility"] == "blocked"
