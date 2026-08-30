"""Evidence-reconciled development protocol enforcement for governed changes.

The committed capability-impact declaration is not trusted merely because it is
well formed.  It is reconciled against repository diff evidence, the existing
capability scanner, persisted structural-fingerprint deltas, and catalog
lineage.  The module never infers or authorizes NEW capability; it only proves
whether a human/AI declaration is consistent with the governed evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Iterable

from .catalog import CapabilityCatalog, CapabilityCatalogError, CapabilityRecord, load_catalog
from .scanner import CapabilityDriftReport, scan_repository

IMPACT_SCHEMA_VERSION = "1.0"
CLASSIFICATIONS = frozenset({"REUSE", "WIRE", "EXTEND", "REPAIR", "REPLACE", "NEW"})
DEFAULT_CATALOG = "governance/capabilities/catalog.json"
DEFAULT_BASELINE = "governance/capabilities/generated/structural_fingerprints.json"
IMPACT_DIRECTORY = "governance/capabilities/impacts"


class DevelopmentProtocolError(ValueError):
    """Raised when development-protocol evidence cannot be loaded safely."""


@dataclass(frozen=True)
class CapabilityImpactDeclaration:
    change_id: str
    classification: str
    capability_ids: tuple[str, ...]
    rationale: str
    supersession_impact: str
    authority_impact: str


@dataclass(frozen=True)
class ChangedPath:
    status: str
    path: str
    previous_path: str | None = None


@dataclass(frozen=True)
class FingerprintDelta:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]

    @property
    def affected_ids(self) -> tuple[str, ...]:
        return tuple(sorted({*self.added, *self.removed, *self.changed}))


@dataclass(frozen=True)
class DevelopmentProtocolReport:
    declaration_required: bool
    declaration: CapabilityImpactDeclaration | None
    fingerprint_delta: FingerprintDelta
    errors: tuple[str, ...]

    @property
    def passes(self) -> bool:
        return not self.errors


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DevelopmentProtocolError(f"{label} must be non-empty text")
    return value.strip()


def load_impact_declaration(path: str | Path) -> CapabilityImpactDeclaration:
    declaration_path = Path(path)
    try:
        raw = json.loads(declaration_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DevelopmentProtocolError(f"cannot load capability-impact declaration: {exc}") from exc
    if not isinstance(raw, dict):
        raise DevelopmentProtocolError("capability-impact declaration root must be an object")
    expected = {
        "schema_version",
        "change_id",
        "classification",
        "capability_ids",
        "rationale",
        "supersession_impact",
        "authority_impact",
    }
    unknown = set(raw) - expected
    missing = expected - set(raw)
    if unknown:
        raise DevelopmentProtocolError(f"unsupported capability-impact keys: {sorted(unknown)}")
    if missing:
        raise DevelopmentProtocolError(f"missing capability-impact keys: {sorted(missing)}")
    if raw.get("schema_version") != IMPACT_SCHEMA_VERSION:
        raise DevelopmentProtocolError(
            f"capability-impact schema_version must be {IMPACT_SCHEMA_VERSION!r}"
        )
    change_id = _nonempty(raw.get("change_id"), "change_id")
    if declaration_path.stem != change_id:
        raise DevelopmentProtocolError("change_id must match the declaration filename stem")
    classification = _nonempty(raw.get("classification"), "classification")
    if classification not in CLASSIFICATIONS:
        raise DevelopmentProtocolError(f"unsupported classification: {classification}")
    capability_ids_raw = raw.get("capability_ids")
    if not isinstance(capability_ids_raw, list) or not capability_ids_raw:
        raise DevelopmentProtocolError("capability_ids must be a non-empty list")
    capability_ids = tuple(_nonempty(item, "capability_ids[]") for item in capability_ids_raw)
    if len(capability_ids) != len(set(capability_ids)):
        raise DevelopmentProtocolError("capability_ids must not contain duplicates")
    rationale_raw = raw.get("rationale")
    if not isinstance(rationale_raw, str):
        raise DevelopmentProtocolError("rationale must be text")
    return CapabilityImpactDeclaration(
        change_id=change_id,
        classification=classification,
        capability_ids=capability_ids,
        rationale=rationale_raw.strip(),
        supersession_impact=_nonempty(raw.get("supersession_impact"), "supersession_impact"),
        authority_impact=_nonempty(raw.get("authority_impact"), "authority_impact"),
    )


def _under(path: str, root: str) -> bool:
    target = Path(path)
    parent = Path(root)
    if target == parent:
        return True
    try:
        target.relative_to(parent)
    except ValueError:
        return False
    return True


def _is_catalog_surface(path: str) -> bool:
    return path == DEFAULT_CATALOG or _under(path, "governance/capabilities/catalog.d")


def _is_baseline_surface(path: str) -> bool:
    return path == DEFAULT_BASELINE


def _is_impact_surface(path: str) -> bool:
    return _under(path, IMPACT_DIRECTORY) and path.endswith(".json")


def _change_paths(change: ChangedPath) -> tuple[str, ...]:
    values = [change.path]
    if change.previous_path is not None:
        values.append(change.previous_path)
    return tuple(values)


def declaration_required(changes: Iterable[ChangedPath], catalog: CapabilityCatalog) -> bool:
    for change in changes:
        for path in _change_paths(change):
            if _is_impact_surface(path):
                continue
            if _is_catalog_surface(path) or _is_baseline_surface(path):
                return True
            if any(_under(path, root) for root in catalog.governed_roots):
                return True
    return False


def _fingerprint_index(payload: object) -> dict[str, tuple[tuple[str, ...], str]]:
    if not isinstance(payload, dict):
        raise DevelopmentProtocolError("fingerprint payload root must be an object")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list):
        raise DevelopmentProtocolError("fingerprint payload capabilities must be a list")
    indexed: dict[str, tuple[tuple[str, ...], str]] = {}
    for raw in capabilities:
        if not isinstance(raw, dict):
            raise DevelopmentProtocolError("fingerprint capability entries must be objects")
        capability_id = raw.get("capability_id")
        paths = raw.get("owned_module_paths")
        fingerprint = raw.get("structural_fingerprint")
        if not isinstance(capability_id, str) or not capability_id:
            raise DevelopmentProtocolError("fingerprint capability_id must be non-empty")
        if capability_id in indexed:
            raise DevelopmentProtocolError(f"duplicate fingerprint capability_id: {capability_id}")
        if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
            raise DevelopmentProtocolError(f"owned_module_paths invalid for {capability_id}")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise DevelopmentProtocolError(f"structural_fingerprint invalid for {capability_id}")
        indexed[capability_id] = (tuple(paths), fingerprint)
    return indexed


def fingerprint_delta(base_payload: object, head_payload: object) -> FingerprintDelta:
    base = _fingerprint_index(base_payload)
    head = _fingerprint_index(head_payload)
    return FingerprintDelta(
        added=tuple(sorted(set(head) - set(base))),
        removed=tuple(sorted(set(base) - set(head))),
        changed=tuple(
            sorted(
                capability_id
                for capability_id in set(base) & set(head)
                if base[capability_id] != head[capability_id]
            )
        ),
    )


def _lineage_state(record: CapabilityRecord | None) -> tuple[object, ...] | None:
    if record is None:
        return None
    return (record.lifecycle_status, record.supersedes, record.superseded_by)


def _added_governed_python_files(
    changes: Iterable[ChangedPath], catalog: CapabilityCatalog
) -> tuple[str, ...]:
    return tuple(
        sorted(
            change.path
            for change in changes
            if change.status == "A"
            and change.path.endswith(".py")
            and any(_under(change.path, root) for root in catalog.governed_roots)
        )
    )


def evaluate_development_protocol(
    *,
    changes: tuple[ChangedPath, ...],
    base_catalog: CapabilityCatalog,
    current_catalog: CapabilityCatalog,
    scanner_report: CapabilityDriftReport,
    base_fingerprints: object,
    current_fingerprints: object,
    declaration: CapabilityImpactDeclaration | None,
) -> DevelopmentProtocolReport:
    required = declaration_required(changes, current_catalog)
    delta = fingerprint_delta(base_fingerprints, current_fingerprints)
    errors: list[str] = []

    impact_changes = tuple(
        change
        for change in changes
        if any(_is_impact_surface(path) for path in _change_paths(change))
    )
    added_impact = tuple(change for change in impact_changes if change.status == "A")
    immutable_violations = tuple(change for change in impact_changes if change.status != "A")
    if immutable_violations:
        errors.append("CAPABILITY_IMPACT_RECORD_IMMUTABLE")
    if required and len(added_impact) != 1:
        errors.append("EXACTLY_ONE_NEW_CAPABILITY_IMPACT_RECORD_REQUIRED")
    if required and declaration is None:
        errors.append("CAPABILITY_IMPACT_DECLARATION_REQUIRED")

    if declaration is not None:
        unknown_ids = sorted(set(declaration.capability_ids) - set(current_catalog.by_id))
        for capability_id in unknown_ids:
            errors.append(f"UNKNOWN_DECLARED_CAPABILITY {capability_id}")

        undeclared = sorted(set(delta.affected_ids) - set(declaration.capability_ids))
        for capability_id in undeclared:
            errors.append(f"UNDECLARED_CAPABILITY_CHANGE {capability_id}")

        for capability_id in delta.removed:
            errors.append(f"CAPABILITY_REMOVAL_REQUIRES_RETAINED_LINEAGE {capability_id}")

        added_governed = _added_governed_python_files(changes, current_catalog)
        if declaration.classification == "REUSE" and added_governed:
            errors.append("REUSE_CANNOT_ADD_GOVERNED_IMPLEMENTATION")

        unclaimed_added = sorted(
            set(added_governed) & set(scanner_report.unclaimed_governed_files)
        )
        for path in unclaimed_added:
            if declaration.classification == "NEW":
                errors.append(f"NEW_CAPABILITY_REQUIRES_CATALOG_REGISTRATION {path}")
            else:
                errors.append(f"UNCLAIMED_GOVERNED_CODE_REQUIRES_NEW_REVIEW {path}")

        if declaration.classification in {"NEW", "REPLACE"} and not declaration.rationale:
            errors.append(f"{declaration.classification}_RATIONALE_REQUIRED")

        base_ids = set(base_catalog.by_id)
        current_ids = set(current_catalog.by_id)
        catalog_added = current_ids - base_ids
        if declaration.classification == "NEW":
            new_declared = catalog_added & set(declaration.capability_ids)
            if not new_declared:
                errors.append("NEW_REQUIRES_NEW_CATALOG_CAPABILITY")
            if not added_governed:
                errors.append("NEW_REQUIRES_ADDED_GOVERNED_IMPLEMENTATION")

        if declaration.classification == "REPLACE":
            if declaration.supersession_impact.casefold() in {"none", "n/a", "na"}:
                errors.append("REPLACE_SUPERSESSION_IMPACT_REQUIRED")
            lineage_changed = any(
                _lineage_state(base_catalog.by_id.get(capability_id))
                != _lineage_state(current_catalog.by_id.get(capability_id))
                for capability_id in declaration.capability_ids
                if capability_id in current_catalog.by_id
            )
            if not lineage_changed:
                errors.append("REPLACE_REQUIRES_CATALOG_LINEAGE_CHANGE")

    return DevelopmentProtocolReport(
        declaration_required=required,
        declaration=declaration,
        fingerprint_delta=delta,
        errors=tuple(dict.fromkeys(errors)),
    )


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise DevelopmentProtocolError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def git_changed_paths(*, repo_root: str | Path, base_ref: str, head_ref: str) -> tuple[ChangedPath, ...]:
    root = Path(repo_root).resolve()
    text = _git(root, "diff", "--name-status", "--find-renames", f"{base_ref}...{head_ref}", "--")
    changes: list[ChangedPath] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status_token = parts[0]
        status = status_token[0]
        if status == "R":
            if len(parts) != 3:
                raise DevelopmentProtocolError(f"cannot parse git rename line: {line}")
            changes.append(ChangedPath(status="R", previous_path=parts[1], path=parts[2]))
        else:
            if len(parts) != 2:
                raise DevelopmentProtocolError(f"cannot parse git diff line: {line}")
            changes.append(ChangedPath(status=status, path=parts[1]))
    return tuple(changes)


def _git_json(repo_root: Path, ref: str, relative_path: str) -> object:
    text = _git(repo_root, "show", f"{ref}:{relative_path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DevelopmentProtocolError(
            f"invalid JSON at {ref}:{relative_path}: {exc}"
        ) from exc


def load_catalog_from_git_ref(
    *, repo_root: str | Path, ref: str, catalog_path: str = DEFAULT_CATALOG
) -> CapabilityCatalog:
    root = Path(repo_root).resolve()
    with tempfile.TemporaryDirectory(prefix="capability-catalog-") as temp:
        temp_root = Path(temp)
        target = temp_root / catalog_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_git(root, "show", f"{ref}:{catalog_path}"), encoding="utf-8")
        fragment_names = _git(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            ref,
            "--",
            "governance/capabilities/catalog.d",
        ).splitlines()
        for relative in fragment_names:
            if not relative.endswith(".json"):
                continue
            fragment = temp_root / relative
            fragment.parent.mkdir(parents=True, exist_ok=True)
            fragment.write_text(_git(root, "show", f"{ref}:{relative}"), encoding="utf-8")
        return load_catalog(target)


def check_development_protocol(
    *,
    repo_root: str | Path,
    base_ref: str,
    head_ref: str,
    catalog_path: str = DEFAULT_CATALOG,
    baseline_path: str = DEFAULT_BASELINE,
) -> DevelopmentProtocolReport:
    root = Path(repo_root).resolve()
    current_catalog = load_catalog(root / catalog_path)
    base_catalog = load_catalog_from_git_ref(repo_root=root, ref=base_ref, catalog_path=catalog_path)
    changes = git_changed_paths(repo_root=root, base_ref=base_ref, head_ref=head_ref)
    scanner_report = scan_repository(repo_root=root, catalog=current_catalog)
    base_fingerprints = _git_json(root, base_ref, baseline_path)
    try:
        current_fingerprints = json.loads((root / baseline_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DevelopmentProtocolError(f"cannot load current fingerprint baseline: {exc}") from exc

    added_impact_paths = tuple(
        change.path
        for change in changes
        if change.status == "A" and _is_impact_surface(change.path)
    )
    declaration: CapabilityImpactDeclaration | None = None
    if len(added_impact_paths) == 1:
        declaration = load_impact_declaration(root / added_impact_paths[0])

    return evaluate_development_protocol(
        changes=changes,
        base_catalog=base_catalog,
        current_catalog=current_catalog,
        scanner_report=scanner_report,
        base_fingerprints=base_fingerprints,
        current_fingerprints=current_fingerprints,
        declaration=declaration,
    )
