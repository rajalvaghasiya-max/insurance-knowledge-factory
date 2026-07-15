"""P1.5c — generic, specification-driven governed migration runner.

Orchestrates the four existing governed migration stages for any Health
product whose configuration is supplied entirely through a governed
migration manifest:

    generic source registration
    -> document classification
    -> product identity reference
    -> document identity resolution

This module contains no insurer-specific or product-specific logic.
All product differences (source path, source hash, specification
paths, output paths, entity identity) are supplied by the manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.generic_source_registration import GenericSourceRegistration
from factory_core.governance.document_classification import DocumentClassificationPolicy
from factory_core.governance.document_identity_resolution import DocumentIdentityResolutionOverlay
from factory_core.governance.product_identity_reference import ProductIdentityReference


class GovernedProductMigrationError(RuntimeError):
    pass


_REQUIRED_SPEC_KEYS = ("generic_registration", "classification", "identity", "overlay")
_REQUIRED_OUTPUT_KEYS = ("bundle", "classification", "identity", "overlay")
_REQUIRED_MANIFEST_KEYS = (
    "domain",
    "insurer_id",
    "product_id",
    "entity_id",
    "expected_source_path",
    "expected_source_sha256",
    "specs",
    "outputs",
)


@dataclass(frozen=True)
class MigrationManifest:
    """Bounded, read-only view of a governed migration manifest."""

    domain: str
    insurer_id: str
    product_id: str
    entity_id: str
    expected_source_path: str
    expected_source_sha256: str
    specs: Mapping[str, str]
    outputs: Mapping[str, str]


def _nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedProductMigrationError(f"{label} must be a non-empty string")
    return value


def load_manifest(manifest_path: str | Path) -> MigrationManifest:
    """Load and structurally validate a governed migration manifest.

    This is a bounded loader, not a general-purpose configuration
    framework: it only accepts the fixed, documented manifest shape.
    """
    path = Path(manifest_path)
    if not path.is_file():
        raise GovernedProductMigrationError(f"Migration manifest was not found: {manifest_path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GovernedProductMigrationError(f"Migration manifest is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise GovernedProductMigrationError("Migration manifest must be a JSON object")

    missing = [key for key in _REQUIRED_MANIFEST_KEYS if key not in raw]
    if missing:
        raise GovernedProductMigrationError("Migration manifest is missing required key(s): " + ", ".join(missing))

    specs = raw["specs"]
    if not isinstance(specs, dict):
        raise GovernedProductMigrationError("Migration manifest 'specs' must be an object")
    missing_specs = [key for key in _REQUIRED_SPEC_KEYS if key not in specs]
    if missing_specs:
        raise GovernedProductMigrationError("Migration manifest 'specs' is missing key(s): " + ", ".join(missing_specs))

    outputs = raw["outputs"]
    if not isinstance(outputs, dict):
        raise GovernedProductMigrationError("Migration manifest 'outputs' must be an object")
    missing_outputs = [key for key in _REQUIRED_OUTPUT_KEYS if key not in outputs]
    if missing_outputs:
        raise GovernedProductMigrationError("Migration manifest 'outputs' is missing key(s): " + ", ".join(missing_outputs))

    return MigrationManifest(
        domain=_nonempty_str(raw["domain"], "domain"),
        insurer_id=_nonempty_str(raw["insurer_id"], "insurer_id"),
        product_id=_nonempty_str(raw["product_id"], "product_id"),
        entity_id=_nonempty_str(raw["entity_id"], "entity_id"),
        expected_source_path=_nonempty_str(raw["expected_source_path"], "expected_source_path"),
        expected_source_sha256=_nonempty_str(raw["expected_source_sha256"], "expected_source_sha256").lower(),
        specs={key: _nonempty_str(specs[key], f"specs.{key}") for key in _REQUIRED_SPEC_KEYS},
        outputs={key: _nonempty_str(outputs[key], f"outputs.{key}") for key in _REQUIRED_OUTPUT_KEYS},
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_expected_source(root: Path, manifest: MigrationManifest) -> Path:
    source = root / manifest.expected_source_path
    if not source.is_file():
        raise GovernedProductMigrationError(
            f"Required immutable source document was not found: {manifest.expected_source_path}"
        )
    actual = sha256_file(source)
    if actual.lower() != manifest.expected_source_sha256:
        raise GovernedProductMigrationError(
            "Source SHA-256 mismatch. Expected "
            f"{manifest.expected_source_sha256}; found {actual}. "
            "Stop: do not register a different document version under this migration."
        )
    return source


def require_spec_files(root: Path, manifest: MigrationManifest) -> None:
    missing = [relative for relative in manifest.specs.values() if not (root / relative).is_file()]
    if missing:
        raise GovernedProductMigrationError("Required migration specification file(s) missing: " + ", ".join(missing))


def run_migration(repository_root: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    manifest = load_manifest(manifest_path)

    require_spec_files(root, manifest)
    source = require_expected_source(root, manifest)

    source_runner = GenericSourceRegistration()
    source_result = source_runner.register_from_spec_file(
        spec_path=root / manifest.specs["generic_registration"], repository_root=root
    )
    bundle_path = source_runner.write_outputs(
        source_result, repository_root=root, bundle_output_path=manifest.outputs["bundle"]
    )

    classification_runner = DocumentClassificationPolicy()
    classification_result = classification_runner.classify_from_spec_file(
        spec_path=root / manifest.specs["classification"], repository_root=root
    )
    classification_path = classification_runner.write_output(
        classification_result, repository_root=root, output_path=manifest.outputs["classification"]
    )

    identity_runner = ProductIdentityReference()
    identity_result = identity_runner.build_from_spec_file(
        spec_path=root / manifest.specs["identity"], repository_root=root
    )
    resolved_entity_id = identity_result.manifest["product_identity"]["entity_id"]
    if resolved_entity_id != manifest.entity_id:
        raise GovernedProductMigrationError(
            "Manifest entity_id does not agree with the resolved product identity. "
            f"Manifest declares {manifest.entity_id!r}; identity specification resolved {resolved_entity_id!r}. "
            "Stop: do not proceed on a mismatched product identity."
        )
    identity_path = identity_runner.write_output(
        identity_result, repository_root=root, output_path=manifest.outputs["identity"]
    )

    overlay_runner = DocumentIdentityResolutionOverlay()
    overlay_result = overlay_runner.build_from_spec_file(
        spec_path=root / manifest.specs["overlay"], repository_root=root
    )
    overlay_path = overlay_runner.write_output(
        overlay_result, repository_root=root, output_path=manifest.outputs["overlay"]
    )

    decision = overlay_result.manifest["documents"][0]["identity_resolution"]
    return {
        "entity_id": overlay_result.manifest["product_identity_reference"]["entity_id"],
        "source_path": str(source),
        "source_sha256": manifest.expected_source_sha256,
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
    parser = argparse.ArgumentParser(
        description="Run the narrow, non-mutating, specification-driven governed product migration."
    )
    parser.add_argument("--migration-spec", required=True, help="Path to a governed migration manifest JSON file.")
    parser.add_argument("--repository-root", required=True)
    args = parser.parse_args()
    result = run_migration(args.repository_root, args.migration_spec)
    print("=" * 70)
    print("GOVERNED PRODUCT MIGRATION")
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
