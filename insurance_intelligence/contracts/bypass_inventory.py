from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class BypassInventoryError(ValueError):
    """Raised when a bypass-inventory record violates the contract."""


class BypassDisposition(str, Enum):
    REMOVED = "REMOVED"
    ROUTED = "ROUTED"
    BLOCKED = "BLOCKED"
    EXPLICITLY_DEFERRED = "EXPLICITLY_DEFERRED"


class BypassReachability(str, Enum):
    ACTIVE_GOVERNED = "ACTIVE_GOVERNED"
    ACTIVE_UNGOVERNED = "ACTIVE_UNGOVERNED"
    CERTIFIED_PILOT_UNREACHABLE = "CERTIFIED_PILOT_UNREACHABLE"
    STATIC_ARTIFACT_UNREACHABLE = "STATIC_ARTIFACT_UNREACHABLE"
    TEST_ONLY = "TEST_ONLY"
    DEAD_OR_OBSOLETE = "DEAD_OR_OBSOLETE"
    UNKNOWN = "UNKNOWN"


class BypassPathKind(str, Enum):
    GOVERNED_CONTROL = "GOVERNED_CONTROL"
    EXECUTABLE_UTILITY = "EXECUTABLE_UTILITY"
    STATIC_ARTIFACT = "STATIC_ARTIFACT"
    TEST_PATH = "TEST_PATH"


@dataclass(frozen=True)
class BypassInventoryEntry:
    path_id: str
    repository_path: str
    path_kind: BypassPathKind
    recommendation_capable: bool
    disposition: BypassDisposition
    reachability: BypassReachability
    certified_pilots: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        for label, value in (
            ("path_id", self.path_id),
            ("repository_path", self.repository_path),
            ("rationale", self.rationale),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BypassInventoryError(f"{label} must be a non-empty string")
        if not isinstance(self.path_kind, BypassPathKind):
            raise BypassInventoryError("path_kind must be a BypassPathKind")
        if not isinstance(self.recommendation_capable, bool):
            raise BypassInventoryError("recommendation_capable must be bool")
        if not isinstance(self.disposition, BypassDisposition):
            raise BypassInventoryError("disposition must be a BypassDisposition")
        if not isinstance(self.reachability, BypassReachability):
            raise BypassInventoryError("reachability must be a BypassReachability")
        if not self.evidence_refs:
            raise BypassInventoryError("evidence_refs must not be empty")
        if len(set(self.certified_pilots)) != len(self.certified_pilots):
            raise BypassInventoryError("certified_pilots must not contain duplicates")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise BypassInventoryError("evidence_refs must not contain duplicates")
        if self.reachability is BypassReachability.ACTIVE_UNGOVERNED:
            raise BypassInventoryError("active ungoverned paths cannot be certified")
        if self.disposition is BypassDisposition.EXPLICITLY_DEFERRED and self.reachability not in {
            BypassReachability.CERTIFIED_PILOT_UNREACHABLE,
            BypassReachability.STATIC_ARTIFACT_UNREACHABLE,
            BypassReachability.TEST_ONLY,
            BypassReachability.DEAD_OR_OBSOLETE,
        }:
            raise BypassInventoryError(
                "explicitly deferred paths must be unreachable, test-only, or obsolete"
            )


@dataclass(frozen=True)
class BypassInventory:
    inventory_id: str
    schema_version: str
    inventory_version: str
    entries: tuple[BypassInventoryEntry, ...]

    def __post_init__(self) -> None:
        if not self.inventory_id.strip():
            raise BypassInventoryError("inventory_id must be non-empty")
        if self.schema_version != "1.0":
            raise BypassInventoryError("schema_version must be 1.0")
        if not self.inventory_version.strip():
            raise BypassInventoryError("inventory_version must be non-empty")
        if not self.entries:
            raise BypassInventoryError("entries must not be empty")
        ids = tuple(item.path_id for item in self.entries)
        paths = tuple(item.repository_path for item in self.entries)
        if len(set(ids)) != len(ids):
            raise BypassInventoryError("path_id values must be unique")
        if len(set(paths)) != len(paths):
            raise BypassInventoryError("repository_path values must be unique")

    def for_pilot(self, pilot_id: str) -> tuple[BypassInventoryEntry, ...]:
        if not isinstance(pilot_id, str) or not pilot_id.strip():
            raise BypassInventoryError("pilot_id must be a non-empty string")
        return tuple(item for item in self.entries if pilot_id in item.certified_pilots)

    def unsafe_reachable_entries(self, pilot_id: str) -> tuple[BypassInventoryEntry, ...]:
        return tuple(
            item
            for item in self.for_pilot(pilot_id)
            if item.recommendation_capable
            and item.reachability is BypassReachability.ACTIVE_UNGOVERNED
        )


def build_inventory(
    *,
    inventory_id: str,
    inventory_version: str,
    entries: Iterable[BypassInventoryEntry],
) -> BypassInventory:
    return BypassInventory(
        inventory_id=inventory_id,
        schema_version="1.0",
        inventory_version=inventory_version,
        entries=tuple(entries),
    )
