"""Repository-derived structural reconciliation for capability governance."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .catalog import CapabilityCatalog

IGNORED_FILENAMES = frozenset({"__init__.py"})


@dataclass(frozen=True)
class CapabilityDriftReport:
    missing_governed_roots: tuple[str, ...]
    missing_ownership_paths: tuple[str, ...]
    unclaimed_governed_files: tuple[str, ...]
    stale_ownership_paths: tuple[str, ...]
    strict_failure_reasons: tuple[str, ...]

    @property
    def structural_drift_detected(self) -> bool:
        return any(
            (
                self.missing_governed_roots,
                self.missing_ownership_paths,
                self.unclaimed_governed_files,
                self.stale_ownership_paths,
            )
        )

    @property
    def passes_enforcement(self) -> bool:
        return not self.strict_failure_reasons


def _iter_governed_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix == ".py" and root.name not in IGNORED_FILENAMES:
            yield root
        return
    for path in sorted(root.rglob("*.py")):
        if path.name in IGNORED_FILENAMES:
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        if "__pycache__" in path.parts:
            continue
        yield path


def _path_is_claimed(relative_path: str, ownership_paths: tuple[str, ...]) -> bool:
    target = Path(relative_path)
    for owned in ownership_paths:
        owner = Path(owned)
        if target == owner:
            return True
        try:
            target.relative_to(owner)
        except ValueError:
            continue
        return True
    return False


def scan_repository(*, repo_root: str | Path, catalog: CapabilityCatalog) -> CapabilityDriftReport:
    root = Path(repo_root).resolve()

    missing_governed_roots: list[str] = []
    governed_files: set[str] = set()
    for configured_root in catalog.governed_roots:
        absolute = root / configured_root
        if not absolute.exists():
            missing_governed_roots.append(configured_root)
            continue
        governed_files.update(
            path.relative_to(root).as_posix() for path in _iter_governed_files(absolute)
        )

    ownership_paths = tuple(
        path
        for capability in catalog.capabilities
        for path in capability.ownership_paths
    )
    missing_ownership_paths = tuple(
        sorted(path for path in ownership_paths if not (root / path).exists())
    )

    unclaimed_governed_files = tuple(
        sorted(
            path
            for path in governed_files
            if not _path_is_claimed(path, ownership_paths)
        )
    )

    stale_ownership_paths = tuple(
        sorted(
            path
            for path in ownership_paths
            if (root / path).exists()
            and (root / path).is_dir()
            and not any(
                _path_is_claimed(file_path, (path,)) for file_path in governed_files
            )
        )
    )

    failure_reasons: list[str] = []
    if missing_governed_roots:
        failure_reasons.append("MISSING_GOVERNED_ROOT")
    if missing_ownership_paths:
        failure_reasons.append("MISSING_OWNERSHIP_PATH")
    if catalog.enforcement_mode == "STRICT" and unclaimed_governed_files:
        failure_reasons.append("UNCLAIMED_GOVERNED_FILE")
    if catalog.enforcement_mode == "STRICT" and stale_ownership_paths:
        failure_reasons.append("STALE_OWNERSHIP_PATH")

    return CapabilityDriftReport(
        missing_governed_roots=tuple(sorted(missing_governed_roots)),
        missing_ownership_paths=missing_ownership_paths,
        unclaimed_governed_files=unclaimed_governed_files,
        stale_ownership_paths=stale_ownership_paths,
        strict_failure_reasons=tuple(failure_reasons),
    )
