"""Read-only discovery for P2.5-F canonical projection pilot inputs.

This module deliberately locates candidates; it never selects a source document,
creates lineage, or infers a product version.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


_SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}


@dataclass(frozen=True)
class DiscoveryResult:
    report: dict[str, Any]


class CanonicalPilotInputDiscovery:
    """Locate review candidates for an existing authoritative rule artifact."""

    def discover(
        self,
        *,
        repository_root: Path | str,
        entity_id: str,
        field: str,
        max_json_bytes: int = 5_000_000,
    ) -> DiscoveryResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Repository root was not found: {root}")
        if not entity_id or not field:
            raise ValueError("entity_id and field are required")

        artifacts: list[dict[str, Any]] = []
        document_reference_candidates: list[dict[str, Any]] = []
        extraction_reference_candidates: list[dict[str, Any]] = []
        parse_failures: list[dict[str, str]] = []

        for path in self._iter_json_files(root):
            try:
                if path.stat().st_size > max_json_bytes:
                    continue
                payload = self._load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                parse_failures.append({"path": self._relative(root, path), "reason": type(exc).__name__})
                continue

            if not isinstance(payload, dict):
                continue
            relative = self._relative(root, path)
            kind = self._classify(payload)

            if self._matches_rule_artifact(payload, entity_id, field):
                artifacts.append({
                    "path": relative,
                    "artifact_kind": kind,
                    "sha256": self._sha256(path),
                    "rule_ids": [item.get("rule_id") for item in payload.get("rules", []) if isinstance(item, dict)],
                    "evidence_ids": self._evidence_ids(payload),
                    "document_ids": self._document_ids(payload),
                })

            # Candidate registries/reports only: this is an inventory, not a semantic match.
            document_ids = self._collect_values(payload, "document_id")
            if document_ids:
                document_reference_candidates.append({
                    "path": relative,
                    "artifact_kind": kind,
                    "document_ids": sorted(document_ids),
                })

            extraction_keys = {"text_path", "extracted_text_path", "processed_text_path", "source_asset_path"}
            extraction_values = {
                key: value
                for key in extraction_keys
                for value in self._collect_values(payload, key)
            }
            if extraction_values:
                extraction_reference_candidates.append({
                    "path": relative,
                    "artifact_kind": kind,
                    "references": extraction_values,
                })

        authoritative = [item for item in artifacts if item["artifact_kind"] == "authoritative_conditional_rule_artifact"]
        report = {
            "schema_version": "1.0",
            "discovery_type": "canonical_projection_pilot_input_discovery_v1",
            "repository_root": str(root),
            "query": {"entity_id": entity_id, "field": field},
            "authoritative_rule_artifact_candidates": authoritative,
            "other_matching_rule_artifact_candidates": [item for item in artifacts if item not in authoritative],
            "document_reference_candidates": document_reference_candidates,
            "extraction_reference_candidates": extraction_reference_candidates,
            "parse_failures": parse_failures,
            "review_required": True,
            "selection_made": False,
            "notes": [
                "This report only locates candidate artifacts and references.",
                "It does not infer document/version identity, extracted-text source, or evidence ranges.",
                "A human must select reviewed inputs before P2.5-D lineage or P2.5-E live projection runs.",
            ],
        }
        return DiscoveryResult(report=report)

    def write_report(self, result: DiscoveryResult, report_path: Path | str) -> Path:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    @staticmethod
    def _load_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _relative(root: Path, path: Path) -> str:
        return path.resolve().relative_to(root).as_posix()

    def _iter_json_files(self, root: Path) -> Iterable[Path]:
        for path in root.rglob("*.json"):
            if any(part in _SKIP_PARTS for part in path.parts):
                continue
            yield path

    @staticmethod
    def _classify(payload: dict[str, Any]) -> str:
        if payload.get("authority_mode") == "authoritative_conditional_rules" and isinstance(payload.get("rules"), list):
            return "authoritative_conditional_rule_artifact"
        if "authoritative_rules_path" in payload and "rule_ids" in payload:
            return "publication_receipt"
        if "document_id" in payload and any(key in payload for key in ("text_path", "extracted_text_path", "processed_text_path")):
            return "document_or_extraction_registry"
        return "json_artifact"

    @staticmethod
    def _matches_rule_artifact(payload: dict[str, Any], entity_id: str, field: str) -> bool:
        return (
            isinstance(payload.get("rules"), list)
            and payload.get("entity_id") == entity_id
            and payload.get("field") == field
        )

    def _evidence_ids(self, payload: dict[str, Any]) -> list[str]:
        ids: set[str] = set()
        for rule in payload.get("rules", []):
            if not isinstance(rule, dict):
                continue
            evidence = rule.get("evidence", {})
            if not isinstance(evidence, dict):
                continue
            for item in [evidence.get("primary_evidence"), *evidence.get("corroborating_evidence", [])]:
                if isinstance(item, dict) and isinstance(item.get("evidence_id"), str):
                    ids.add(item["evidence_id"])
        return sorted(ids)

    def _document_ids(self, payload: dict[str, Any]) -> list[str]:
        ids: set[str] = set()
        for rule in payload.get("rules", []):
            if not isinstance(rule, dict):
                continue
            evidence = rule.get("evidence", {})
            if not isinstance(evidence, dict):
                continue
            for item in [evidence.get("primary_evidence"), *evidence.get("corroborating_evidence", [])]:
                if isinstance(item, dict) and isinstance(item.get("document_id"), str):
                    ids.add(item["document_id"])
        return sorted(ids)

    def _collect_values(self, value: Any, key: str) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for current_key, current_value in value.items():
                if current_key == key and isinstance(current_value, str):
                    found.add(current_value)
                found.update(self._collect_values(current_value, key))
        elif isinstance(value, list):
            for item in value:
                found.update(self._collect_values(item, key))
        return found
