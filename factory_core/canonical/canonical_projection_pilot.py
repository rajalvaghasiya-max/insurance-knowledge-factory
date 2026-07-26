"""P2.5-E controlled canonical projection pilot.

This module orchestrates the already-certified P2.5-C adapter against a
P2.5-D lineage-manifest file. It is read-only with respect to legacy rule
artifacts, receipts, documents, and extracted text. The canonical projection
is written separately only after all lineage and authority checks pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .legacy_conditional_rule_adapter import (
    CanonicalProductContext,
    CanonicalProjection,
    LegacyConditionalRuleAdapter,
    LegacyConditionalRuleProjectionError,
)


class CanonicalProjectionPilotError(ValueError):
    """Raised when a pilot specification cannot be executed truthfully."""


@dataclass(frozen=True)
class CanonicalProjectionPilotResult:
    projection: CanonicalProjection
    report: Mapping[str, Any]


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalProjectionPilotError(f"{label} must be a JSON object")
    return value


def _require_nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalProjectionPilotError(f"{label} must be a non-empty string")
    return value


def _load_json(path: Path, label: str) -> tuple[Mapping[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {path}")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalProjectionPilotError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    return _require_mapping(parsed, label), _sha256_bytes(raw)


def _resolve_under_root(root: Path, raw_path: object, label: str) -> Path:
    relative_path = Path(_require_nonempty(raw_path, label))
    if relative_path.is_absolute():
        raise CanonicalProjectionPilotError(f"{label} must be relative to repository_root")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative_path).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CanonicalProjectionPilotError(f"{label} must remain under repository_root") from exc
    return resolved


def _context_from(raw: object) -> CanonicalProductContext:
    data = _require_mapping(raw, "pilot_spec.product_context")
    required = (
        "insurer_id",
        "insurer_legal_name",
        "product_id",
        "product_name",
        "domain",
        "product_version_id",
    )
    values = {key: _require_nonempty(data.get(key), f"pilot_spec.product_context.{key}") for key in required}
    optional = {
        key: (None if data.get(key) is None else _require_nonempty(data.get(key), f"pilot_spec.product_context.{key}"))
        for key in ("insurer_type", "product_version_label", "product_uin", "product_family_name")
    }
    return CanonicalProductContext(**values, **optional)


def _unwrap_bridge_manifest(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept either a raw P2.5-C manifest or a P2.5-D bridge wrapper."""
    if "lineage_manifest" in raw:
        wrapper_version = raw.get("schema_version")
        if wrapper_version != "1.0":
            raise CanonicalProjectionPilotError("bridge manifest wrapper schema_version must be 1.0")
        return _require_mapping(raw["lineage_manifest"], "bridge_manifest.lineage_manifest")
    return raw


class CanonicalProjectionPilot:
    """Runs one controlled, source-preserving canonical projection."""

    def run_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
    ) -> CanonicalProjectionPilotResult:
        spec_file = Path(spec_path)
        raw_spec, _ = _load_json(spec_file, "pilot specification")
        return self.run(spec=raw_spec, repository_root=repository_root, source_spec_path=spec_file)

    def run(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        source_spec_path: Path | None = None,
    ) -> CanonicalProjectionPilotResult:
        spec = _require_mapping(spec, "pilot_spec")
        if spec.get("schema_version") != "1.0":
            raise CanonicalProjectionPilotError("pilot_spec.schema_version must be 1.0")
        if spec.get("pilot_type") != "canonical_projection_pilot_v1":
            raise CanonicalProjectionPilotError("pilot_spec.pilot_type must be canonical_projection_pilot_v1")
        root = Path(repository_root)
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")

        rules_path = _resolve_under_root(root, spec.get("rules_path"), "pilot_spec.rules_path")
        receipt_path = _resolve_under_root(root, spec.get("publication_receipt_path"), "pilot_spec.publication_receipt_path")
        lineage_path = _resolve_under_root(root, spec.get("lineage_manifest_path"), "pilot_spec.lineage_manifest_path")
        output_path = _resolve_under_root(root, spec.get("output_path"), "pilot_spec.output_path")
        # Output may not exist yet; only its parent needs to be safely located.
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rules, rules_sha256 = _load_json(rules_path, "rules artifact")
        receipt, receipt_sha256 = _load_json(receipt_path, "publication receipt")
        raw_lineage, lineage_file_sha256 = _load_json(lineage_path, "lineage manifest")
        lineage_manifest = _unwrap_bridge_manifest(raw_lineage)
        context = _context_from(spec.get("product_context"))

        before = {path: path.read_bytes() for path in (rules_path, receipt_path, lineage_path)}
        try:
            projection = LegacyConditionalRuleAdapter().project(
                rules_artifact=rules,
                publication_receipt=receipt,
                lineage_manifest=lineage_manifest,
                context=context,
                rules_sha256=rules_sha256,
                receipt_sha256=receipt_sha256,
                lineage_manifest_sha256=lineage_file_sha256,
                source_paths={
                    "rules_path": rules_path.relative_to(root.resolve()).as_posix(),
                    "publication_receipt_path": receipt_path.relative_to(root.resolve()).as_posix(),
                    "lineage_manifest_path": lineage_path.relative_to(root.resolve()).as_posix(),
                    "pilot_spec_path": (source_spec_path.resolve().relative_to(root.resolve()).as_posix() if source_spec_path and source_spec_path.resolve().is_relative_to(root.resolve()) else None),
                },
            )
        except LegacyConditionalRuleProjectionError as exc:
            raise CanonicalProjectionPilotError(str(exc)) from exc

        LegacyConditionalRuleAdapter().write_projection(projection, output_path)
        after = {path: path.read_bytes() for path in before}
        if after != before:
            raise CanonicalProjectionPilotError("Pilot modified a source artifact; projection was rejected")

        report = {
            "schema_version": "1.0",
            "pilot_type": "canonical_projection_pilot_v1",
            "pilot_status": "validated_read_only_canonical_projection",
            "output_path": output_path.relative_to(root.resolve()).as_posix(),
            "rules_sha256": rules_sha256,
            "publication_receipt_sha256": receipt_sha256,
            "lineage_manifest_file_sha256": lineage_file_sha256,
            "mapping_counts": projection.report["mapping_counts"],
            "notes": [
                "Legacy rule artifacts, publication receipts, documents, and extracted text were read-only inputs.",
                "The bridge-wrapper hash is retained as the lineage source artifact hash when a P2.5-D wrapper is supplied.",
                "Canonical projection output is a separate derived artifact and does not alter publication authority.",
            ],
        }
        return CanonicalProjectionPilotResult(projection=projection, report=report)

    def write_report(self, result: CanonicalProjectionPilotResult, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(result.report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
