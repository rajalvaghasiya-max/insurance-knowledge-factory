"""P2.5-F1 registry integrity diagnostics and pilot-source recovery.

Read-only by design. This module never repairs, rewrites, renames, moves, or
quarantines repository files. It produces a review manifest identifying broken
registry files and explicit source-reference candidates for a target document id.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

_SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}
_DEFAULT_REGISTRY_PATHS = (
    "registry/document_registry.json",
    "registry/product_families.json",
    "registry/uin_registry.json",
)


@dataclass(frozen=True)
class RegistryIntegrityRecoveryResult:
    report: dict[str, Any]


class RegistryIntegrityAndPilotSourceRecovery:
    """Diagnose registry integrity and locate only explicit source references."""

    def analyze(
        self,
        *,
        repository_root: Path | str,
        document_id: str,
        registry_paths: Iterable[str] = _DEFAULT_REGISTRY_PATHS,
        max_json_bytes: int = 5_000_000,
    ) -> RegistryIntegrityRecoveryResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Repository root was not found: {root}")
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id is required")
        if max_json_bytes <= 0:
            raise ValueError("max_json_bytes must be positive")

        registry_diagnostics = [self._diagnose_registry(root, raw_path) for raw_path in registry_paths]
        explicit_references, parse_failures = self._find_explicit_document_references(
            root=root,
            document_id=document_id.strip(),
            max_json_bytes=max_json_bytes,
        )
        source_assets = self._resolve_explicit_source_assets(root, explicit_references)

        registry_blockers = [
            item["path"] for item in registry_diagnostics
            if item["integrity_status"] != "valid_json"
        ]
        unresolved = not bool(source_assets)
        report = {
            "schema_version": "1.0",
            "recovery_type": "registry_integrity_and_pilot_source_recovery_v1",
            "repository_root": str(root),
            "document_id": document_id.strip(),
            "read_only": True,
            "registry_diagnostics": registry_diagnostics,
            "registry_blockers": registry_blockers,
            "explicit_document_reference_candidates": explicit_references,
            "explicit_source_asset_candidates": source_assets,
            "source_recovery_status": "unresolved" if unresolved else "review_required",
            "parse_failures_outside_target_registries": parse_failures,
            "repair_plan": {
                "automatic_repair_performed": False,
                "quarantine_action_performed": False,
                "required_human_actions": self._required_human_actions(registry_diagnostics, source_assets),
            },
            "notes": [
                "Only exact document_id matches in parseable JSON are treated as reference candidates.",
                "A candidate path is not treated as provenance unless a parseable artifact explicitly links it to the target document_id.",
                "No filename, folder name, timestamp, or policy wording text is used to infer document identity.",
                "Malformed registry files are fingerprinted for review; no automated repair or quarantine is performed.",
            ],
        }
        return RegistryIntegrityRecoveryResult(report=report)

    def write_report(self, result: RegistryIntegrityRecoveryResult, report_path: Path | str) -> Path:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def _diagnose_registry(self, root: Path, raw_path: str) -> dict[str, Any]:
        candidate = (root / raw_path).resolve()
        record: dict[str, Any] = {"path": self._safe_relative(root, candidate)}
        if not self._within_root(root, candidate):
            return {**record, "integrity_status": "unsafe_path", "exists": False}
        if not candidate.exists():
            return {**record, "integrity_status": "missing", "exists": False}
        if not candidate.is_file():
            return {**record, "integrity_status": "not_a_file", "exists": True}
        raw = candidate.read_bytes()
        record.update({"exists": True, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            return {
                **record,
                "integrity_status": "invalid_utf8",
                "error": {"type": type(exc).__name__, "start": exc.start, "end": exc.end},
            }
        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError as exc:
            return {
                **record,
                "integrity_status": "invalid_json",
                "error": {"type": type(exc).__name__, "line": exc.lineno, "column": exc.colno, "position": exc.pos},
            }
        return {
            **record,
            "integrity_status": "valid_json",
            "root_type": type(payload).__name__,
            "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        }

    def _find_explicit_document_references(
        self, *, root: Path, document_id: str, max_json_bytes: int
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        candidates: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        for path in self._iter_json_files(root):
            try:
                if path.stat().st_size > max_json_bytes:
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                failures.append({"path": self._safe_relative(root, path), "reason": type(exc).__name__})
                continue
            if not isinstance(payload, (dict, list)):
                continue
            occurrences = self._document_id_occurrences(payload, document_id)
            if not occurrences:
                continue
            references = self._extract_explicit_paths_near_document(payload, document_id)
            candidates.append({
                "path": self._safe_relative(root, path),
                "sha256": self._sha256(path),
                "document_id_occurrences": occurrences,
                "explicit_source_paths": references,
            })
        candidates.sort(key=lambda item: item["path"])
        return candidates, failures

    def _resolve_explicit_source_assets(self, root: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        assets: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            for source_path in candidate.get("explicit_source_paths", []):
                parsed = Path(source_path)
                # Absolute paths are intentionally not accepted as portable provenance.
                if parsed.is_absolute():
                    continue
                resolved = (root / parsed).resolve()
                if not self._within_root(root, resolved) or not resolved.is_file():
                    continue
                relative = self._safe_relative(root, resolved)
                assets[relative] = {
                    "path": relative,
                    "bytes": resolved.stat().st_size,
                    "sha256": self._sha256(resolved),
                    "referenced_by": sorted({
                        *assets.get(relative, {}).get("referenced_by", []),
                        candidate["path"],
                    }),
                }
        return [assets[key] for key in sorted(assets)]

    @staticmethod
    def _document_id_occurrences(value: Any, document_id: str) -> int:
        if isinstance(value, dict):
            return sum(
                1 if key == "document_id" and current == document_id else 0
                for key, current in value.items()
            ) + sum(RegistryIntegrityAndPilotSourceRecovery._document_id_occurrences(v, document_id) for v in value.values())
        if isinstance(value, list):
            return sum(RegistryIntegrityAndPilotSourceRecovery._document_id_occurrences(item, document_id) for item in value)
        return 0

    @staticmethod
    def _extract_explicit_paths_near_document(value: Any, document_id: str) -> list[str]:
        keys = {"source_path", "document_path", "raw_document_path", "text_path", "extracted_text_path", "processed_text_path"}
        found: set[str] = set()
        if isinstance(value, dict):
            if value.get("document_id") == document_id:
                for key in keys:
                    path = value.get(key)
                    if isinstance(path, str):
                        found.add(path)
            for nested in value.values():
                found.update(RegistryIntegrityAndPilotSourceRecovery._extract_explicit_paths_near_document(nested, document_id))
        elif isinstance(value, list):
            for nested in value:
                found.update(RegistryIntegrityAndPilotSourceRecovery._extract_explicit_paths_near_document(nested, document_id))
        return sorted(found)

    @staticmethod
    def _required_human_actions(registry_diagnostics: list[dict[str, Any]], assets: list[dict[str, Any]]) -> list[str]:
        actions: list[str] = []
        for item in registry_diagnostics:
            if item["integrity_status"] == "invalid_json":
                actions.append(f"Review and repair {item['path']} from a known-good source; preserve its recorded SHA-256 before replacement.")
            elif item["integrity_status"] == "missing":
                actions.append(f"Confirm whether {item['path']} is intentionally absent or restore it from version control/backup.")
        if not assets:
            actions.append("Provide or register one reviewed source document and one reviewed extracted-text asset explicitly bound to the target document_id.")
        actions.append("Create a reviewed P2.5-D lineage specification only after source-document and extracted-text bindings are explicit.")
        return actions

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _within_root(root: Path, path: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    @staticmethod
    def _safe_relative(root: Path, path: Path) -> str:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return str(path)

    @staticmethod
    def _iter_json_files(root: Path) -> Iterable[Path]:
        for path in root.rglob("*.json"):
            if any(part in _SKIP_PARTS for part in path.parts):
                continue
            yield path
