"""P1.5c — governed migration of one legacy Bajaj My Health Care policy wording."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

from factory_core.canonical.generic_source_registration import GenericSourceRegistration
from factory_core.governance.document_classification import DocumentClassificationPolicy
from factory_core.governance.document_identity_resolution import DocumentIdentityResolutionOverlay
from factory_core.governance.product_identity_reference import ProductIdentityReference

EXPECTED_POLICY_WORDING_SHA256 = "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade"
SOURCE_RELATIVE_PATH = "archive/raw_pdf/bajaj_allianz_general/policy_wording/My-Health-Care-Plan1-PW__9479fe6f6ce7.pdf"
SPECS = {
    "generic_registration": "docs/architecture/bajaj_my_health_care_generic_sources_registration_spec.json",
    "classification": "docs/architecture/bajaj_my_health_care_document_classification_spec.json",
    "identity": "docs/architecture/bajaj_my_health_care_product_identity_reference_spec.json",
    "overlay": "docs/architecture/bajaj_my_health_care_document_identity_resolution_spec.json",
}
OUTPUTS = {
    "bundle": "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/generic_source_registration/bajaj_my_health_care_generic_source_bundle.json",
    "classification": "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/governance/bajaj_my_health_care_document_classification.json",
    "identity": "knowledge/factory/product_identity_references/bajaj_allianz_general_my_health_care.product_identity_reference.json",
    "overlay": "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/governance/bajaj_my_health_care_document_identity_resolution.json",
}

class BajajGovernedMigrationError(RuntimeError):
    pass

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def require_expected_source(root: Path) -> Path:
    source = root / SOURCE_RELATIVE_PATH
    if not source.is_file():
        raise BajajGovernedMigrationError(f"Required immutable policy wording was not found: {SOURCE_RELATIVE_PATH}")
    actual = sha256_file(source)
    if actual.lower() != EXPECTED_POLICY_WORDING_SHA256:
        raise BajajGovernedMigrationError(
            "Policy wording SHA-256 mismatch. Expected "
            f"{EXPECTED_POLICY_WORDING_SHA256}; found {actual}. "
            "Stop: do not register a different document version under this migration."
        )
    return source

def require_spec_files(root: Path) -> None:
    missing = [relative for relative in SPECS.values() if not (root / relative).is_file()]
    if missing:
        raise BajajGovernedMigrationError("Required migration specification file(s) missing: " + ", ".join(missing))

def run_migration(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    require_spec_files(root)
    source = require_expected_source(root)
    source_runner = GenericSourceRegistration()
    source_result = source_runner.register_from_spec_file(spec_path=root / SPECS["generic_registration"], repository_root=root)
    bundle_path = source_runner.write_outputs(source_result, repository_root=root, bundle_output_path=OUTPUTS["bundle"])
    classification_runner = DocumentClassificationPolicy()
    classification_result = classification_runner.classify_from_spec_file(spec_path=root / SPECS["classification"], repository_root=root)
    classification_path = classification_runner.write_output(classification_result, repository_root=root, output_path=OUTPUTS["classification"])
    identity_runner = ProductIdentityReference()
    identity_result = identity_runner.build_from_spec_file(spec_path=root / SPECS["identity"], repository_root=root)
    identity_path = identity_runner.write_output(identity_result, repository_root=root, output_path=OUTPUTS["identity"])
    overlay_runner = DocumentIdentityResolutionOverlay()
    overlay_result = overlay_runner.build_from_spec_file(spec_path=root / SPECS["overlay"], repository_root=root)
    overlay_path = overlay_runner.write_output(overlay_result, repository_root=root, output_path=OUTPUTS["overlay"])
    decision = overlay_result.manifest["documents"][0]["identity_resolution"]
    return {
        "entity_id": overlay_result.manifest["product_identity_reference"]["entity_id"],
        "source_path": str(source),
        "source_sha256": EXPECTED_POLICY_WORDING_SHA256,
        "bundle_output_path": str(bundle_path),
        "classification_output_path": str(classification_path),
        "identity_output_path": str(identity_path),
        "overlay_output_path": str(overlay_path),
        "source_registration_status": source_result.bundle["registration_status"],
        "classification_status": classification_result.manifest["classification_status"],
        "identity_status": identity_result.manifest["identity_resolution_status"],
        "overlay_status": overlay_result.manifest["overlay_status"],
        "resolution_status": decision["resolution_status"],
        "temporal_status": decision["temporal_status"],
        "evidence_review_eligibility": decision["evidence_review_eligibility"],
        "current_entitlement_publication_eligibility": decision["current_entitlement_publication_eligibility"],
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Run the narrow, non-mutating Bajaj My Health Care governed migration.")
    parser.add_argument("--repository-root", required=True)
    args = parser.parse_args()
    result = run_migration(args.repository_root)
    print("=" * 70)
    print("BAJAJ MY HEALTH CARE — GOVERNED MIGRATION")
    print("=" * 70)
    print(f"Product              : {result['entity_id']}")
    print(f"Source SHA-256       : {result['source_sha256']}")
    print(f"Source registration  : {result['source_registration_status']}")
    print(f"Classification       : {result['classification_status']}")
    print(f"Identity             : {result['identity_status']}")
    print(f"Resolution           : {result['resolution_status']}")
    print(f"Temporal             : {result['temporal_status']}")
    print(f"Evidence review      : {result['evidence_review_eligibility']}")
    print(f"Current entitlement  : {result['current_entitlement_publication_eligibility']}")
    print(f"Overlay              : {result['overlay_output_path']}")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
