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
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from factory_core.canonical.generic_source_registration import GenericSourceRegistration
from factory_core.governance.document_classification import DocumentClassificationPolicy
from factory_core.governance.document_identity_resolution import DocumentIdentityResolutionOverlay
from factory_core.governance.product_identity_reference import ProductIdentityReference


class GovernedProductMigrationError(RuntimeError):
    pass


_SUPPORTED_SCHEMA_VERSION = "1.0"
_SUPPORTED_MANIFEST_TYPE = "governed_product_migration_manifest_v1"
_SUPPORTED_DOMAIN = "health"
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")

_REQUIRED_SPEC_KEYS = ("generic_registration", "classification", "identity", "overlay")
_REQUIRED_OUTPUT_KEYS = ("bundle", "classification", "identity", "overlay")
_REQUIRED_MANIFEST_KEYS = (
    "schema_version",
    "manifest_type",
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


def _safe_relative_path(value: object, label: str) -> str:
    """Structural path-safety check, independent of repository_root, and
    independent of the host operating system's own Path.is_absolute()
    interpretation.

    pathlib.Path(...).is_absolute() alone is not reliable here: on a
    Windows host it does not classify POSIX-rooted paths like
    '/etc/passwd' as absolute, and on a POSIX host it does not classify
    Windows drive-qualified or UNC paths as absolute. This check
    explicitly evaluates the candidate under PurePosixPath,
    PureWindowsPath, and the host-native Path, and rejects it if any of
    those interpretations, or a leading UNC marker, or a drive letter,
    consider it non-relative. It also rejects any '..' traversal
    component under either POSIX or Windows path splitting.

    A second, repository_root-aware check (_resolve_under_root) is
    applied at usage time as defense in depth.
    """
    text = _nonempty_str(value, label)
    if (
        Path(text).is_absolute()
        or PurePosixPath(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
        or text.startswith("\\\\")
        or (":" in text[:3])
    ):
        raise GovernedProductMigrationError(
            f"{label} must be a repository-relative path; found an absolute, drive-qualified, or UNC path: {text!r}"
        )
    if ".." in PurePosixPath(text).parts or ".." in PureWindowsPath(text).parts:
        raise GovernedProductMigrationError(f"{label} must not contain '..' path traversal: {text!r}")
    return text


def _resolve_under_root(root: Path, relative: str, label: str) -> Path:
    resolved_root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise GovernedProductMigrationError(
            f"{label} must resolve inside repository_root; {relative!r} escapes {resolved_root}"
        ) from exc
    return candidate


def _validate_sha256(value: object, label: str) -> str:
    text = _nonempty_str(value, label)
    if not _SHA256_PATTERN.match(text):
        raise GovernedProductMigrationError(f"{label} must be exactly 64 hexadecimal characters")
    return text.lower()


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

    if raw.get("schema_version") != _SUPPORTED_SCHEMA_VERSION:
        raise GovernedProductMigrationError(f"Migration manifest schema_version must be {_SUPPORTED_SCHEMA_VERSION!r}")
    if raw.get("manifest_type") != _SUPPORTED_MANIFEST_TYPE:
        raise GovernedProductMigrationError(f"Migration manifest manifest_type must be {_SUPPORTED_MANIFEST_TYPE!r}")
    if raw.get("domain") != _SUPPORTED_DOMAIN:
        raise GovernedProductMigrationError(
            f"Migration manifest domain must be {_SUPPORTED_DOMAIN!r}; this runner supports Health only"
        )

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
        expected_source_path=_safe_relative_path(raw["expected_source_path"], "expected_source_path"),
        expected_source_sha256=_validate_sha256(raw["expected_source_sha256"], "expected_source_sha256"),
        specs={key: _safe_relative_path(specs[key], f"specs.{key}") for key in _REQUIRED_SPEC_KEYS},
        outputs={key: _safe_relative_path(outputs[key], f"outputs.{key}") for key in _REQUIRED_OUTPUT_KEYS},
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_expected_source(root: Path, manifest: MigrationManifest) -> Path:
    source = _resolve_under_root(root, manifest.expected_source_path, "expected_source_path")
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
    missing = []
    for label, relative in manifest.specs.items():
        candidate = _resolve_under_root(root, relative, f"specs.{label}")
        if not candidate.is_file():
            missing.append(relative)
    if missing:
        raise GovernedProductMigrationError("Required migration specification file(s) missing: " + ", ".join(missing))


def run_migration(repository_root: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    manifest = load_manifest(manifest_path)

    require_spec_files(root, manifest)
    source = require_expected_source(root, manifest)

    # Defense in depth: every configured spec/output path must independently
    # resolve inside repository_root, in addition to the structural
    # (relative, no '..') check already performed by load_manifest.
    for label, relative in manifest.specs.items():
        _resolve_under_root(root, relative, f"specs.{label}")
    for label, relative in manifest.outputs.items():
        _resolve_under_root(root, relative, f"outputs.{label}")

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
    overlay_entity_id = overlay_result.manifest["product_identity_reference"]["entity_id"]
    if overlay_entity_id != manifest.entity_id or overlay_entity_id != resolved_entity_id:
        raise GovernedProductMigrationError(
            "Overlay entity_id does not agree with the migration manifest and/or the product identity "
            f"stage. Overlay resolved {overlay_entity_id!r}; manifest declares {manifest.entity_id!r}; "
            f"identity stage resolved {resolved_entity_id!r}. Stop: do not proceed on a mismatched product identity."
        )
    overlay_path = overlay_runner.write_output(
        overlay_result, repository_root=root, output_path=manifest.outputs["overlay"]
    )

    decision = overlay_result.manifest["documents"][0]["identity_resolution"]
    return {
        "entity_id": overlay_entity_id,
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
        description="Run the narrow, specification-driven governed product migration."
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
