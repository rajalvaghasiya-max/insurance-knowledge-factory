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

BAJAJ_MANIFEST_PATH = "docs/architecture/bajaj_my_health_care_migration_manifest.json"


def _write_manifest(tmp_path, **overrides):
    manifest = {
        "schema_version": "1.0",
        "manifest_type": "governed_product_migration_manifest_v1",
        "domain": "health",
        "insurer_id": "bajaj_allianz_general",
        "product_id": "my_health_care",
        "entity_id": "bajaj_allianz_general:my_health_care",
        "expected_source_path": "source.pdf",
        "expected_source_sha256": "0" * 64,
        "specs": {
            "generic_registration": "generic_registration_spec.json",
            "classification": "classification_spec.json",
            "identity": "identity_spec.json",
            "overlay": "overlay_spec.json",
        },
        "outputs": {
            "bundle": "outputs/bundle.json",
            "classification": "outputs/classification.json",
            "identity": "outputs/identity.json",
            "overlay": "outputs/overlay.json",
        },
    }
    manifest.update(overrides)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_bajaj_manifest_loads_and_matches_approved_values():
    manifest = load_manifest(BAJAJ_MANIFEST_PATH)
    assert manifest.entity_id == "bajaj_allianz_general:my_health_care"
    assert manifest.expected_source_sha256 == "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade"
    assert manifest.specs["identity"] == "docs/architecture/bajaj_my_health_care_product_identity_reference_spec.json"
    assert manifest.outputs["identity"] == (
        "knowledge/factory/product_identity_references/bajaj_allianz_general_my_health_care.product_identity_reference.json"
    )


def test_missing_manifest_required_key_fails_closed(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"domain": "health"}), encoding="utf-8")
    with pytest.raises(GovernedProductMigrationError, match="missing required key"):
        load_manifest(manifest_path)


def test_unsupported_schema_version_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path, schema_version="2.0")
    with pytest.raises(GovernedProductMigrationError, match="schema_version must be"):
        load_manifest(manifest_path)


def test_incorrect_manifest_type_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path, manifest_type="some_other_manifest_v1")
    with pytest.raises(GovernedProductMigrationError, match="manifest_type must be"):
        load_manifest(manifest_path)


def test_malformed_sha256_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path, expected_source_sha256="not-a-real-hash")
    with pytest.raises(GovernedProductMigrationError, match="64 hexadecimal characters"):
        load_manifest(manifest_path)


def test_malformed_sha256_wrong_length_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path, expected_source_sha256="ab" * 30)
    with pytest.raises(GovernedProductMigrationError, match="64 hexadecimal characters"):
        load_manifest(manifest_path)


def test_unsupported_domain_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path, domain="motor")
    with pytest.raises(GovernedProductMigrationError, match="domain must be"):
        load_manifest(manifest_path)


def test_absolute_configured_path_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path, expected_source_path="/etc/passwd")
    with pytest.raises(GovernedProductMigrationError, match="absolute, drive-qualified, or UNC"):
        load_manifest(manifest_path)


def test_absolute_spec_path_fails_closed(tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        specs={
            "generic_registration": "/absolute/registration_spec.json",
            "classification": "classification_spec.json",
            "identity": "identity_spec.json",
            "overlay": "overlay_spec.json",
        },
    )
    with pytest.raises(GovernedProductMigrationError, match="absolute, drive-qualified, or UNC"):
        load_manifest(manifest_path)


def test_posix_rooted_path_rejected_regardless_of_host_os(tmp_path):
    """pathlib.Path(...).is_absolute() alone does not classify a
    POSIX-rooted path as absolute on a Windows host. This must be
    rejected regardless of the host operating system."""
    manifest_path = _write_manifest(tmp_path, expected_source_path="/etc/passwd")
    with pytest.raises(GovernedProductMigrationError, match="absolute, drive-qualified, or UNC"):
        load_manifest(manifest_path)


def test_windows_drive_qualified_path_rejected(tmp_path):
    for candidate in (r"C:\absolute\registration_spec.json", "C:/absolute/registration_spec.json"):
        manifest_path = _write_manifest(tmp_path, expected_source_path=candidate)
        with pytest.raises(GovernedProductMigrationError, match="absolute, drive-qualified, or UNC"):
            load_manifest(manifest_path)


def test_unc_path_rejected(tmp_path):
    manifest_path = _write_manifest(tmp_path, expected_source_path=r"\\server\share\registration_spec.json")
    with pytest.raises(GovernedProductMigrationError, match="absolute, drive-qualified, or UNC"):
        load_manifest(manifest_path)


def test_windows_style_traversal_rejected(tmp_path):
    manifest_path = _write_manifest(tmp_path, expected_source_path=r"..\..\etc\passwd")
    with pytest.raises(GovernedProductMigrationError, match="path traversal"):
        load_manifest(manifest_path)


def test_repository_path_traversal_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path, expected_source_path="../../etc/passwd")
    with pytest.raises(GovernedProductMigrationError, match="path traversal"):
        load_manifest(manifest_path)


def test_repository_path_traversal_in_output_fails_closed(tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        outputs={
            "bundle": "../escaped_bundle.json",
            "classification": "outputs/classification.json",
            "identity": "outputs/identity.json",
            "overlay": "outputs/overlay.json",
        },
    )
    with pytest.raises(GovernedProductMigrationError, match="path traversal"):
        load_manifest(manifest_path)


def test_valid_repository_relative_paths_are_accepted(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_path)
    assert manifest.expected_source_path == "source.pdf"
    assert manifest.specs["identity"] == "identity_spec.json"
    assert manifest.outputs["identity"] == "outputs/identity.json"


def test_missing_source_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    # Create the four spec files referenced so we get past the spec-existence
    # check and reach the source-file check specifically.
    (tmp_path / "generic_registration_spec.json").write_text("{}")
    (tmp_path / "classification_spec.json").write_text("{}")
    (tmp_path / "identity_spec.json").write_text("{}")
    (tmp_path / "overlay_spec.json").write_text("{}")
    with pytest.raises(GovernedProductMigrationError, match="source document was not found"):
        run_migration(tmp_path, manifest_path)


def test_source_hash_mismatch_fails_closed(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"not the approved document")
    actual_hash = hashlib.sha256(b"not the approved document").hexdigest()
    assert actual_hash != "0" * 64
    manifest_path = _write_manifest(tmp_path)
    for name in ("generic_registration_spec.json", "classification_spec.json", "identity_spec.json", "overlay_spec.json"):
        (tmp_path / name).write_text("{}")
    with pytest.raises(GovernedProductMigrationError, match="SHA-256 mismatch"):
        run_migration(tmp_path, manifest_path)


def test_missing_specification_fails_closed(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    # Deliberately do not create any of the four spec files.
    with pytest.raises(GovernedProductMigrationError, match="specification file"):
        run_migration(tmp_path, manifest_path)


def test_generic_runner_contains_no_insurer_or_product_branching():
    source_text = open("scripts/run_governed_product_migration.py", encoding="utf-8").read().lower()
    forbidden_terms = [
        "bajaj",
        "allianz",
        "my_health_care",
        "my-health-care",
        "star_health",
        "star_comprehensive",
        "aditya_birla",
        "activ_one",
    ]
    found = [term for term in forbidden_terms if term in source_text]
    assert found == [], f"generic runner contains insurer/product-specific literal(s): {found}"


class _FakeSourceResult:
    bundle = {"registration_status": "generic_sources_registered_evidence_review_required"}


class _FakeClassificationResult:
    manifest = {"classification_status": "reviewed_document_classifications_recorded_not_published"}


_REGISTRATION_OUTPUT_RELATIVE = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/"
    "generic_source_registration/policy_wording_registration.json"
)
_CLASSIFICATION_OUTPUT_RELATIVE = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/"
    "governance/bajaj_my_health_care_document_classification.json"
)


def _seed_registration_and_classification_fixtures(root):
    """Pre-place the exact on-disk artifacts the real, unmocked identity and
    overlay stages read via _load_json -- as if source registration and
    classification had already completed successfully. Only the two stages
    that require the archive PDF (registration build, classification build)
    are given fixture data here; the identity and document-identity-
    resolution overlay stages that follow run against the real, unmodified
    Bajaj specifications and contracts, unchanged."""
    registration_path = root / _REGISTRATION_OUTPUT_RELATIVE
    registration_path.parent.mkdir(parents=True, exist_ok=True)
    registration_path.write_text(
        json.dumps(
            {
                "document": {
                    "document_id": "bajaj_my_health_care_policy_wording_v1",
                    "document_version_id": "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade",
                    "source_document_id": "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade",
                    "document_type": "policy_wording",
                    "content_sha256": "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade",
                }
            }
        ),
        encoding="utf-8",
    )
    classification_path = root / _CLASSIFICATION_OUTPUT_RELATIVE
    classification_path.parent.mkdir(parents=True, exist_ok=True)
    classification_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_version_id": "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade",
                        "classification": "reusable_generic",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _run_with_seeded_evidence_stages(root):
    """Exercise the real generic runner, the real Bajaj identity and overlay
    specifications/contracts, and the real Bajaj manifest -- mocking only
    the two build calls that require the archive PDF that cannot be present
    in this environment (source registration, classification), while their
    on-disk outputs are pre-seeded as real, schema-valid fixture files so
    the downstream identity and overlay stages read genuine data from disk,
    not a mock."""
    with patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.register_from_spec_file",
        return_value=_FakeSourceResult(),
    ), patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.write_outputs",
        return_value=root / "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/generic_source_registration/bajaj_my_health_care_generic_source_bundle.json",
    ), patch(
        "scripts.run_governed_product_migration.DocumentClassificationPolicy.classify_from_spec_file",
        return_value=_FakeClassificationResult(),
    ), patch(
        "scripts.run_governed_product_migration.DocumentClassificationPolicy.write_output",
        return_value=root / _CLASSIFICATION_OUTPUT_RELATIVE,
    ), patch(
        "scripts.run_governed_product_migration.require_expected_source",
        return_value=root / "archive/raw_pdf/bajaj_allianz_general/policy_wording/My-Health-Care-Plan1-PW__9479fe6f6ce7.pdf",
    ):
        return run_migration(root, BAJAJ_MANIFEST_PATH)


def _prepare_shadow_repository_root(tmp_path):
    """Copy only the real, approved specification files and manifest into a
    disposable temp repository root, plus seed the registration/
    classification fixtures, so identity/overlay outputs are written under
    tmp_path rather than into the real repository tree."""
    import shutil

    for relative in (
        "docs/architecture/bajaj_my_health_care_migration_manifest.json",
        "docs/architecture/bajaj_my_health_care_product_identity_reference_spec.json",
        "docs/architecture/bajaj_my_health_care_document_identity_resolution_spec.json",
        "docs/architecture/bajaj_my_health_care_document_classification_spec.json",
        "docs/architecture/bajaj_my_health_care_generic_sources_registration_spec.json",
    ):
        source = Path(relative)
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    _seed_registration_and_classification_fixtures(tmp_path)
    return tmp_path


def test_valid_bajaj_execution_reproduces_approved_governance_states(tmp_path):
    root = _prepare_shadow_repository_root(tmp_path)
    result = _run_with_seeded_evidence_stages(root)
    assert result["entity_id"] == "bajaj_allianz_general:my_health_care"
    assert result["source_registration_status"] == "generic_sources_registered_evidence_review_required"
    assert result["classification_status"] == "reviewed_document_classifications_recorded_not_published"
    assert result["identity_status"] == "resolved"
    assert result["resolution_status"] == "resolved"
    assert result["temporal_status"] == "compatibility_unverified"
    assert result["evidence_review_eligibility"] == "eligible_for_evidence_review"
    assert result["current_entitlement_publication_eligibility"] == "blocked"


def test_manifest_identity_mismatch_fails_closed(tmp_path):
    root = _prepare_shadow_repository_root(tmp_path)
    manifest = json.loads((root / BAJAJ_MANIFEST_PATH).read_text(encoding="utf-8"))
    manifest["entity_id"] = "bajaj_allianz_general:a_different_product"
    mismatched_manifest_path = root / "mismatched_manifest.json"
    mismatched_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.register_from_spec_file",
        return_value=_FakeSourceResult(),
    ), patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.write_outputs",
        return_value=root / "ignored.json",
    ), patch(
        "scripts.run_governed_product_migration.require_expected_source",
        return_value=root / "ignored.pdf",
    ):
        with pytest.raises(GovernedProductMigrationError, match="does not agree with the resolved product identity"):
            run_migration(root, mismatched_manifest_path)


def test_overlay_identity_mismatch_fails_closed(tmp_path):
    """The manifest and the identity stage's in-memory result may agree,
    but if the identity record actually persisted to disk (and thus read
    back by the overlay stage) disagrees -- e.g. a stale or tampered file --
    the overlay-stage cross-check must independently catch it."""
    root = _prepare_shadow_repository_root(tmp_path)

    def _write_tampered_identity_output(result, *, repository_root, output_path):
        tampered = json.loads(json.dumps(dict(result.manifest)))
        tampered["product_identity"] = dict(tampered["product_identity"])
        tampered["product_identity"]["entity_id"] = "bajaj_allianz_general:tampered_product"
        tampered["product_identity"]["product_id"] = "tampered_product"
        target = Path(repository_root) / output_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(tampered), encoding="utf-8")
        return target

    with patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.register_from_spec_file",
        return_value=_FakeSourceResult(),
    ), patch(
        "scripts.run_governed_product_migration.GenericSourceRegistration.write_outputs",
        return_value=root / "ignored_bundle.json",
    ), patch(
        "scripts.run_governed_product_migration.DocumentClassificationPolicy.classify_from_spec_file",
        return_value=_FakeClassificationResult(),
    ), patch(
        "scripts.run_governed_product_migration.DocumentClassificationPolicy.write_output",
        return_value=root / _CLASSIFICATION_OUTPUT_RELATIVE,
    ), patch(
        "scripts.run_governed_product_migration.require_expected_source",
        return_value=root / "ignored.pdf",
    ), patch(
        "scripts.run_governed_product_migration.ProductIdentityReference.write_output",
        side_effect=_write_tampered_identity_output,
    ):
        with pytest.raises(GovernedProductMigrationError, match="Overlay entity_id does not agree"):
            run_migration(root, BAJAJ_MANIFEST_PATH)


def test_deterministic_semantic_output_across_two_runs(tmp_path):
    root_a = _prepare_shadow_repository_root(tmp_path / "run_a")
    root_b = _prepare_shadow_repository_root(tmp_path / "run_b")
    result_a = _run_with_seeded_evidence_stages(root_a)
    result_b = _run_with_seeded_evidence_stages(root_b)

    semantic_keys = (
        "entity_id",
        "source_sha256",
        "source_registration_status",
        "classification_status",
        "identity_status",
        "overlay_status",
        "resolution_status",
        "temporal_status",
        "evidence_review_eligibility",
        "current_entitlement_publication_eligibility",
    )
    for key in semantic_keys:
        assert result_a[key] == result_b[key], f"{key} differs between runs: {result_a[key]!r} vs {result_b[key]!r}"


def test_bajaj_compatibility_sha_constant_matches_governed_manifest():
    from scripts.run_bajaj_my_health_care_governed_migration import EXPECTED_POLICY_WORDING_SHA256

    manifest = load_manifest(BAJAJ_MANIFEST_PATH)
    assert EXPECTED_POLICY_WORDING_SHA256 == manifest.expected_source_sha256
    assert EXPECTED_POLICY_WORDING_SHA256 == "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade"


def test_bajaj_wrapper_importable_from_external_working_directory(tmp_path, monkeypatch):
    """The wrapper's compatibility constant must resolve correctly even
    when the process current working directory is not the repository
    root -- it must be anchored to the module's own file location, not
    to CWD-relative manifest loading."""
    import importlib
    import scripts.run_bajaj_my_health_care_governed_migration as bajaj_wrapper

    external_dir = tmp_path / "somewhere_else_entirely"
    external_dir.mkdir()
    monkeypatch.chdir(external_dir)

    reloaded = importlib.reload(bajaj_wrapper)

    expected_manifest = load_manifest(
        Path(reloaded.__file__).resolve().parents[1] / "docs/architecture/bajaj_my_health_care_migration_manifest.json"
    )
    assert reloaded.EXPECTED_POLICY_WORDING_SHA256 == expected_manifest.expected_source_sha256
    assert reloaded.EXPECTED_POLICY_WORDING_SHA256 == "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade"


def test_thin_bajaj_wrapper_delegates_without_duplicated_logic():
    from scripts.run_bajaj_my_health_care_governed_migration import run_bajaj_migration

    with patch("scripts.run_bajaj_my_health_care_governed_migration.run_migration") as mock_run:
        mock_run.return_value = {"entity_id": "bajaj_allianz_general:my_health_care"}
        result = run_bajaj_migration(".")
        assert mock_run.called
        called_root, called_manifest = mock_run.call_args[0]
        assert str(called_manifest).endswith("bajaj_my_health_care_migration_manifest.json")
        assert result == {"entity_id": "bajaj_allianz_general:my_health_care"}

    wrapper_source = open(
        "scripts/run_bajaj_my_health_care_governed_migration.py", encoding="utf-8"
    ).read()
    orchestration_markers = ["sha256_file(", "GenericSourceRegistration()", "DocumentClassificationPolicy()"]
    found = [marker for marker in orchestration_markers if marker in wrapper_source]
    assert found == [], f"thin wrapper contains duplicated orchestration logic: {found}"
