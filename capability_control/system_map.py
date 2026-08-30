"""Deterministic human-readable capability map derived from governed repository memory.

This module is a compact view layer only. It does not create capability identity,
lifecycle, authority, reuse policy, safety invariants, or roadmap decisions. Detailed
semantic truth remains in the validated capability catalog; structural implementation
evidence comes from the committed fingerprint baseline.
"""
from __future__ import annotations

import json
from pathlib import Path

from capability_control.catalog import CapabilityCatalog, CapabilityRecord, load_catalog


class CapabilitySystemMapError(ValueError):
    """Raised when the generated system map cannot be reconciled."""


def _load_fingerprint_index(path: str | Path) -> tuple[dict[str, dict[str, object]], str]:
    fingerprint_path = Path(path)
    try:
        raw = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilitySystemMapError(f"cannot load structural fingerprints: {exc}") from exc
    if not isinstance(raw, dict):
        raise CapabilitySystemMapError("structural fingerprint root must be an object")
    records = raw.get("capabilities")
    if not isinstance(records, list):
        raise CapabilitySystemMapError("structural fingerprints must contain a capabilities list")
    index: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise CapabilitySystemMapError("structural fingerprint capability entries must be objects")
        capability_id = record.get("capability_id")
        fingerprint = record.get("structural_fingerprint")
        paths = record.get("owned_module_paths")
        if not isinstance(capability_id, str) or not capability_id:
            raise CapabilitySystemMapError("structural fingerprint entry has invalid capability_id")
        if capability_id in index:
            raise CapabilitySystemMapError(f"duplicate structural fingerprint: {capability_id}")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise CapabilitySystemMapError(f"invalid structural fingerprint: {capability_id}")
        if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
            raise CapabilitySystemMapError(f"invalid owned_module_paths: {capability_id}")
        index[capability_id] = record
    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise CapabilitySystemMapError("structural fingerprint schema_version must be present")
    return index, schema_version


def _lineage(record: CapabilityRecord) -> str:
    pieces: list[str] = []
    if record.supersedes:
        pieces.append("supersedes " + ", ".join(f"`{item}`" for item in record.supersedes))
    if record.superseded_by is not None:
        pieces.append(f"superseded by `{record.superseded_by}`")
    return "; ".join(pieces) if pieces else "None"


def _render_capability(record: CapabilityRecord, fingerprint: dict[str, object]) -> list[str]:
    structural_fingerprint = fingerprint["structural_fingerprint"]
    assert isinstance(structural_fingerprint, str)
    lines = [
        f"### `{record.capability_id}` — {record.name}",
        "",
        f"- **Lifecycle:** `{record.lifecycle_status}`",
        f"- **Reuse policy:** `{record.reuse_policy}`",
        f"- **Authority role:** {record.authority_role}",
        f"- **Lineage:** {_lineage(record)}",
        f"- **Structural fingerprint:** `{structural_fingerprint}`",
        "- **Ownership boundary:**",
    ]
    lines.extend(f"  - `{path}`" for path in record.ownership_paths)
    lines.append("")
    return lines


def render_capability_map(
    catalog: CapabilityCatalog,
    fingerprint_index: dict[str, dict[str, object]],
    *,
    fingerprint_schema_version: str,
) -> str:
    catalog_ids = {record.capability_id for record in catalog.capabilities}
    fingerprint_ids = set(fingerprint_index)
    if catalog_ids != fingerprint_ids:
        missing = sorted(catalog_ids - fingerprint_ids)
        extra = sorted(fingerprint_ids - catalog_ids)
        raise CapabilitySystemMapError(
            f"catalog/fingerprint capability mismatch missing={missing} extra={extra}"
        )

    by_plane: dict[str, list[CapabilityRecord]] = {}
    for record in catalog.capabilities:
        by_plane.setdefault(record.plane, []).append(record)

    lines = [
        "# PolicyScna Generated Capability Map",
        "",
        "> **GENERATED — DO NOT EDIT.** Deterministic navigation view of the validated semantic capability catalog plus the committed structural fingerprint baseline. Detailed responsibility, safety invariants, notes and module-level structural evidence remain in their canonical machine sources. This map does not authorize roadmap or next actions.",
        "",
        "## Control-plane state",
        "",
        f"- **Catalog version:** `{catalog.catalog_version}`",
        f"- **Enforcement mode:** `{catalog.enforcement_mode}`",
        f"- **Fingerprint schema:** `{fingerprint_schema_version}`",
        f"- **Registered capabilities:** `{len(catalog.capabilities)}`",
        "- **Governed roots:** " + ", ".join(f"`{root}`" for root in catalog.governed_roots),
        "",
        "## Interpretation rules",
        "",
        "- Executable code and passing tests remain the highest repository evidence.",
        "- Structural fingerprints bind registered implementation to capabilities; they do not infer semantic authority.",
        "- Ownership boundaries shown here are semantic catalog ownership paths; exact module-level structural evidence remains in the fingerprint manifest/inventory.",
        "- The semantic catalog remains the detailed source for responsibility, safety invariants, lifecycle, reuse policy, ownership and lineage.",
        "- Execution priorities and authorized next actions belong in the execution ledger / blocker record, not in this map.",
        "- Unregistered governed files remain reconciliation candidates while enforcement mode is `RECONCILIATION`.",
        "",
        "## Capabilities by plane",
        "",
    ]
    for plane in sorted(by_plane):
        lines.extend([f"## {plane}", ""])
        for record in sorted(by_plane[plane], key=lambda item: item.capability_id):
            lines.extend(_render_capability(record, fingerprint_index[record.capability_id]))
    return "\n".join(lines).rstrip() + "\n"


def generate_capability_map(
    catalog_path: str | Path,
    fingerprint_path: str | Path,
) -> str:
    catalog = load_catalog(catalog_path)
    fingerprint_index, schema_version = _load_fingerprint_index(fingerprint_path)
    return render_capability_map(
        catalog,
        fingerprint_index,
        fingerprint_schema_version=schema_version,
    )
