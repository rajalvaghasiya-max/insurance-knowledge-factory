"""Semantic catalog contract for PolicyScna capability governance.

The catalog intentionally stores only facts that are not safely derivable from
the repository tree: responsibility, authority role, lifecycle, reuse policy,
ownership boundaries and lineage. File existence and structural coverage are
verified by the scanner rather than copied into parallel documentation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

CATALOG_VERSION = "1.0"
CAPABILITY_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:\.[A-Z0-9_]+)+$")
LIFECYCLE_STATUSES = frozenset(
    {"ACTIVE", "DISCONNECTED", "EXPERIMENTAL", "SUPERSEDED", "LEGACY"}
)
REUSE_POLICIES = frozenset(
    {"REUSE", "WIRE", "EXTEND", "REPAIR", "REPLACE_ONLY_WITH_EXPLICIT_LINEAGE", "LEGACY_ONLY"}
)
ENFORCEMENT_MODES = frozenset({"RECONCILIATION", "STRICT"})

_TOP_LEVEL_KEYS = frozenset(
    {"catalog_version", "enforcement_mode", "governed_roots", "capabilities"}
)
_CAPABILITY_KEYS = frozenset(
    {
        "capability_id",
        "name",
        "responsibility",
        "plane",
        "lifecycle_status",
        "authority_role",
        "safety_invariants",
        "reuse_policy",
        "ownership_paths",
        "introduced_by",
        "supersedes",
        "superseded_by",
        "notes",
    }
)


class CapabilityCatalogError(ValueError):
    """Raised when the semantic capability catalog is invalid."""


def _require_nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityCatalogError(f"{label} must be a non-empty string")
    return value.strip()


def _require_string_list(value: object, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CapabilityCatalogError(f"{label} must be a list")
    items = tuple(_require_nonempty(item, f"{label}[]") for item in value)
    if not allow_empty and not items:
        raise CapabilityCatalogError(f"{label} must not be empty")
    if len(set(items)) != len(items):
        raise CapabilityCatalogError(f"{label} must not contain duplicates")
    return items


def _validate_relative_path(value: str, label: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CapabilityCatalogError(f"{label} must be a repository-relative path")
    normalized = path.as_posix().rstrip("/")
    if not normalized or normalized == ".":
        raise CapabilityCatalogError(f"{label} must identify a repository surface")
    return normalized


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    name: str
    responsibility: str
    plane: str
    lifecycle_status: str
    authority_role: str
    safety_invariants: tuple[str, ...]
    reuse_policy: str
    ownership_paths: tuple[str, ...]
    introduced_by: str | None
    supersedes: tuple[str, ...]
    superseded_by: str | None
    notes: str | None


@dataclass(frozen=True)
class CapabilityCatalog:
    catalog_version: str
    enforcement_mode: str
    governed_roots: tuple[str, ...]
    capabilities: tuple[CapabilityRecord, ...]

    @property
    def by_id(self) -> dict[str, CapabilityRecord]:
        return {record.capability_id: record for record in self.capabilities}


def _parse_record(raw: object, index: int) -> CapabilityRecord:
    if not isinstance(raw, dict):
        raise CapabilityCatalogError(f"capabilities[{index}] must be an object")
    unknown = set(raw) - _CAPABILITY_KEYS
    if unknown:
        raise CapabilityCatalogError(
            f"capabilities[{index}] contains unsupported keys: {sorted(unknown)}"
        )

    capability_id = _require_nonempty(raw.get("capability_id"), f"capabilities[{index}].capability_id")
    if not CAPABILITY_ID_RE.fullmatch(capability_id):
        raise CapabilityCatalogError(
            f"capabilities[{index}].capability_id has invalid stable-ID syntax"
        )

    lifecycle_status = _require_nonempty(
        raw.get("lifecycle_status"), f"capabilities[{index}].lifecycle_status"
    )
    if lifecycle_status not in LIFECYCLE_STATUSES:
        raise CapabilityCatalogError(f"unsupported lifecycle_status: {lifecycle_status}")

    reuse_policy = _require_nonempty(
        raw.get("reuse_policy"), f"capabilities[{index}].reuse_policy"
    )
    if reuse_policy not in REUSE_POLICIES:
        raise CapabilityCatalogError(f"unsupported reuse_policy: {reuse_policy}")

    ownership_paths = tuple(
        _validate_relative_path(item, f"capabilities[{index}].ownership_paths[]")
        for item in _require_string_list(
            raw.get("ownership_paths"), f"capabilities[{index}].ownership_paths"
        )
    )

    introduced_by_raw = raw.get("introduced_by")
    introduced_by = (
        None
        if introduced_by_raw is None
        else _require_nonempty(introduced_by_raw, f"capabilities[{index}].introduced_by")
    )
    supersedes = _require_string_list(
        raw.get("supersedes", []), f"capabilities[{index}].supersedes", allow_empty=True
    )
    superseded_by_raw = raw.get("superseded_by")
    superseded_by = (
        None
        if superseded_by_raw is None
        else _require_nonempty(superseded_by_raw, f"capabilities[{index}].superseded_by")
    )
    notes_raw = raw.get("notes")
    notes = None if notes_raw is None else _require_nonempty(notes_raw, f"capabilities[{index}].notes")

    return CapabilityRecord(
        capability_id=capability_id,
        name=_require_nonempty(raw.get("name"), f"capabilities[{index}].name"),
        responsibility=_require_nonempty(
            raw.get("responsibility"), f"capabilities[{index}].responsibility"
        ),
        plane=_require_nonempty(raw.get("plane"), f"capabilities[{index}].plane"),
        lifecycle_status=lifecycle_status,
        authority_role=_require_nonempty(
            raw.get("authority_role"), f"capabilities[{index}].authority_role"
        ),
        safety_invariants=_require_string_list(
            raw.get("safety_invariants"), f"capabilities[{index}].safety_invariants"
        ),
        reuse_policy=reuse_policy,
        ownership_paths=ownership_paths,
        introduced_by=introduced_by,
        supersedes=supersedes,
        superseded_by=superseded_by,
        notes=notes,
    )


def validate_catalog(raw: object) -> CapabilityCatalog:
    if not isinstance(raw, dict):
        raise CapabilityCatalogError("catalog root must be an object")
    unknown = set(raw) - _TOP_LEVEL_KEYS
    if unknown:
        raise CapabilityCatalogError(f"catalog contains unsupported keys: {sorted(unknown)}")

    version = _require_nonempty(raw.get("catalog_version"), "catalog_version")
    if version != CATALOG_VERSION:
        raise CapabilityCatalogError(f"catalog_version must be {CATALOG_VERSION!r}")

    enforcement_mode = _require_nonempty(raw.get("enforcement_mode"), "enforcement_mode")
    if enforcement_mode not in ENFORCEMENT_MODES:
        raise CapabilityCatalogError(f"unsupported enforcement_mode: {enforcement_mode}")

    governed_roots = tuple(
        _validate_relative_path(item, "governed_roots[]")
        for item in _require_string_list(raw.get("governed_roots"), "governed_roots")
    )

    capabilities_raw = raw.get("capabilities")
    if not isinstance(capabilities_raw, list) or not capabilities_raw:
        raise CapabilityCatalogError("capabilities must be a non-empty list")
    capabilities = tuple(_parse_record(record, index) for index, record in enumerate(capabilities_raw))

    ids = [record.capability_id for record in capabilities]
    if len(ids) != len(set(ids)):
        raise CapabilityCatalogError("capability_id values must be unique")

    ownership: dict[str, str] = {}
    for record in capabilities:
        for path in record.ownership_paths:
            owner = ownership.get(path)
            if owner is not None:
                raise CapabilityCatalogError(
                    f"ownership path {path!r} is claimed by both {owner} and {record.capability_id}"
                )
            ownership[path] = record.capability_id

    known_ids = set(ids)
    for record in capabilities:
        for prior in record.supersedes:
            if prior not in known_ids:
                raise CapabilityCatalogError(
                    f"{record.capability_id} supersedes unknown capability {prior}"
                )
            if prior == record.capability_id:
                raise CapabilityCatalogError("a capability cannot supersede itself")
        if record.superseded_by is not None:
            if record.superseded_by not in known_ids:
                raise CapabilityCatalogError(
                    f"{record.capability_id} is superseded by unknown capability {record.superseded_by}"
                )
            if record.superseded_by == record.capability_id:
                raise CapabilityCatalogError("a capability cannot be superseded by itself")

    for record in capabilities:
        if record.lifecycle_status == "SUPERSEDED" and record.superseded_by is None:
            raise CapabilityCatalogError(
                f"SUPERSEDED capability {record.capability_id} must declare superseded_by"
            )
        if record.superseded_by is not None:
            successor = next(item for item in capabilities if item.capability_id == record.superseded_by)
            if record.capability_id not in successor.supersedes:
                raise CapabilityCatalogError(
                    f"supersession lineage must be bidirectional between {record.capability_id} and {successor.capability_id}"
                )

    return CapabilityCatalog(
        catalog_version=version,
        enforcement_mode=enforcement_mode,
        governed_roots=governed_roots,
        capabilities=capabilities,
    )


def _load_fragment_records(fragment_dir: Path) -> list[object]:
    records: list[object] = []
    if not fragment_dir.exists():
        return records
    if not fragment_dir.is_dir():
        raise CapabilityCatalogError(f"catalog fragment path is not a directory: {fragment_dir}")
    for fragment_path in sorted(fragment_dir.glob("*.json")):
        try:
            raw = json.loads(fragment_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CapabilityCatalogError(
                f"cannot load capability catalog fragment {fragment_path.name}: {exc}"
            ) from exc
        if not isinstance(raw, dict) or set(raw) != {"capabilities"}:
            raise CapabilityCatalogError(
                f"catalog fragment {fragment_path.name} must contain only a capabilities list"
            )
        values = raw.get("capabilities")
        if not isinstance(values, list) or not values:
            raise CapabilityCatalogError(
                f"catalog fragment {fragment_path.name} capabilities must be a non-empty list"
            )
        records.extend(values)
    return records


def load_catalog(path: str | Path) -> CapabilityCatalog:
    catalog_path = Path(path)
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilityCatalogError(f"cannot load capability catalog: {exc}") from exc
    if not isinstance(raw, dict):
        raise CapabilityCatalogError("catalog root must be an object")
    merged = dict(raw)
    base_capabilities = merged.get("capabilities")
    if not isinstance(base_capabilities, list):
        raise CapabilityCatalogError("capabilities must be a list before fragment merge")
    merged["capabilities"] = [
        *base_capabilities,
        *_load_fragment_records(catalog_path.with_name("catalog.d")),
    ]
    return validate_catalog(merged)
