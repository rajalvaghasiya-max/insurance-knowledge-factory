from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.factory.pipeline_status import default_pipeline_status


@dataclass(frozen=True)
class RegistryBackedFactoryBridgePaths:
    project_root: Path
    intake_registry_path: Path
    parse_registry_path: Path
    quality_registry_path: Path
    factory_input_registry_path: Path
    report_path: Path


class RegistryBackedFactoryBridge:
    """Build Department III work inputs from registry-backed parse artifacts.

    This adapter deliberately does not modify the legacy Evidence Registry.
    The legacy registry was designed for discovery-derived raw evidence. This
    bridge produces a separate, explicit Factory Input Registry containing
    only quality-approved parsed evidence artifacts whose raw-source lineage
    is already known.
    """

    VERSION = "1.0"
    REGISTRY_VERSION = "1.0"

    def __init__(self, project_root: Path | None = None):
        root = Path(project_root or BASE_DIR).resolve()
        registry_dir = root / "registry"
        self.paths = RegistryBackedFactoryBridgePaths(
            project_root=root,
            intake_registry_path=registry_dir / "product_evidence_intake_registry.json",
            parse_registry_path=registry_dir / "pdf_parse_registry.json",
            quality_registry_path=registry_dir / "pdf_parse_quality_registry.json",
            factory_input_registry_path=registry_dir / "registry_backed_factory_input_registry.json",
            report_path=root / "reports" / "registry_backed_factory_bridge_report.json",
        )

    def build(self, *, entity_id: str, write: bool = True) -> dict[str, Any]:
        intake = self._load_required(self.paths.intake_registry_path)
        parse_registry = self._load_required(self.paths.parse_registry_path)
        quality_registry = self._load_required(self.paths.quality_registry_path)

        intake_by_key = {
            self._record_key(record): record
            for record in intake.get("records", [])
            if record.get("entity_id") == entity_id
        }
        parse_by_key = {
            self._record_key(record): record
            for record in parse_registry.get("records", [])
            if record.get("entity_id") == entity_id
        }
        quality_by_key = {
            self._record_key(record): record
            for record in quality_registry.get("records", [])
            if record.get("entity_id") == entity_id
        }

        records: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        for key in sorted(intake_by_key):
            intake_record = intake_by_key[key]
            parse_record = parse_by_key.get(key)
            quality_record = quality_by_key.get(key)

            issues: list[str] = []
            if intake_record.get("intake_status") != "ready_for_processing":
                issues.append(f"intake_status={intake_record.get('intake_status')}")
            if not parse_record:
                issues.append("missing_parse_registry_record")
            if not quality_record:
                issues.append("missing_quality_registry_record")
            elif quality_record.get("quality_status") != "ready_for_extraction":
                issues.append(f"quality_status={quality_record.get('quality_status')}")

            parse_artifact_path: Path | None = None
            if parse_record:
                output_path = parse_record.get("output_path")
                if not isinstance(output_path, str) or not output_path.strip():
                    issues.append("missing_parse_output_path")
                else:
                    parse_artifact_path = self.paths.project_root / output_path
                    if not parse_artifact_path.exists():
                        issues.append("missing_parse_output_file")

            if issues:
                blocked.append(
                    {
                        "entity_id": entity_id,
                        "document_type": intake_record.get("document_type"),
                        "source_document_id": intake_record.get("source_document_id"),
                        "status": "blocked",
                        "reasons": issues,
                    }
                )
                continue

            assert parse_record is not None
            assert quality_record is not None
            assert parse_artifact_path is not None
            records.append(self._build_factory_input_record(
                intake_record=intake_record,
                parse_record=parse_record,
                quality_record=quality_record,
                parse_artifact_path=parse_artifact_path,
            ))

        insurer_id = self._single_value(records, "insurer_id")
        product_name = self._single_value(records, "product_name")
        factory_registry = {
            "registry_version": self.REGISTRY_VERSION,
            "bridge_version": self.VERSION,
            "generated_at": self._utc_now(),
            "registry_kind": "registry_backed_factory_input",
            "entity_id": entity_id,
            "insurer_id": insurer_id,
            "product_name": product_name,
            "document_count": len(records),
            "blocked_count": len(blocked),
            "documents": records,
            "blocked_records": blocked,
            "notes": [
                "This registry is a Department III execution input, not a replacement for the legacy discovery-derived Evidence Registry.",
                "Each document points to a parsed JSON artifact and retains the immutable raw PDF source hash and archive path.",
                "Only records with intake_status=ready_for_processing and quality_status=ready_for_extraction are included.",
            ],
        }
        report = {
            "schema_version": "1.0",
            "bridge_version": self.VERSION,
            "generated_at": self._utc_now(),
            "entity_id": entity_id,
            "factory_input_registry": self._relative(self.paths.factory_input_registry_path),
            "status_counts": {
                "ready_for_department_03": len(records),
                "blocked": len(blocked),
            },
            "records": [
                {
                    "document_id": record["document_id"],
                    "document_type": record["document_type"],
                    "source_document_id": record["source_document_id"],
                    "relative_path": record["relative_path"],
                    "raw_evidence_relative_path": record["raw_evidence_relative_path"],
                    "quality_status": record["quality_status"],
                    "status": "ready_for_department_03",
                }
                for record in records
            ],
            "blocked_records": blocked,
            "notes": [
                "No raw PDF, parsed artifact, or legacy evidence registry record is modified by this bridge.",
                "The Factory Manager must be invoked with --registry-path pointing to this registry.",
            ],
        }

        if write:
            self._write_json(self.paths.factory_input_registry_path, factory_registry)
            self._write_json(self.paths.report_path, report)
        return {"registry": factory_registry, "report": report}

    def _build_factory_input_record(
        self,
        *,
        intake_record: dict[str, Any],
        parse_record: dict[str, Any],
        quality_record: dict[str, Any],
        parse_artifact_path: Path,
    ) -> dict[str, Any]:
        raw_sha256 = str(intake_record["sha256"])
        parser_version = str(parse_record.get("parser_version") or "unknown")
        parse_artifact_hash = self._file_hash(parse_artifact_path)
        processing_input_hash = self._stable_hash(
            f"{raw_sha256}|{parse_artifact_hash}|{parser_version}|{self.VERSION}"
        )
        document_id = self._stable_id(
            "doc",
            f"registry_backed|{intake_record['entity_id']}|{intake_record['source_document_id']}",
        )
        source_type = intake_record.get("document_type")
        return {
            "document_id": document_id,
            "insurer_id": intake_record.get("insurer_id"),
            "product_name": intake_record.get("product_name"),
            "artifact_type": "parsed_evidence",
            "document_type": source_type,
            "source_type": source_type,
            "evidence_role": intake_record.get("evidence_role"),
            "authority_score": intake_record.get("authority_score"),
            "entity_ids": [intake_record["entity_id"]],
            "entity_matches": [
                {
                    "entity_id": intake_record["entity_id"],
                    "match_reason": "registry_backed_product_evidence_intake",
                    "matched_aliases": [],
                }
            ],
            "relative_path": self._relative(parse_artifact_path),
            "path": str(parse_artifact_path),
            "document_hash": raw_sha256,
            "source_document_id": intake_record["source_document_id"],
            "source_url": intake_record.get("source_url"),
            "source_page_url": intake_record.get("source_page_url"),
            "raw_evidence_relative_path": intake_record.get("relative_archive_path"),
            "raw_evidence_path": intake_record.get("captured_local_path"),
            "parse_id": parse_record.get("parse_id"),
            "parse_artifact_hash": parse_artifact_hash,
            "parser_version": parser_version,
            "quality_audit_id": quality_record.get("quality_audit_id"),
            "quality_status": quality_record.get("quality_status"),
            "processing_input_hash": processing_input_hash,
            "logical_document_key": f"{source_type}|{intake_record['entity_id']}|{raw_sha256}",
            "file_size_bytes": parse_artifact_path.stat().st_size,
            "modified_at": datetime.fromtimestamp(parse_artifact_path.stat().st_mtime, tz=timezone.utc).isoformat(),
            "effective_date": None,
            "version_label": parser_version,
            "status": "active",
            "registration_source": "registry_backed_factory_bridge",
            "registry_notes": [
                "Registry-backed parsed evidence; raw source PDF remains immutable in archive/raw_pdf.",
                "Eligible for Department III because parse quality audit is ready_for_extraction.",
            ],
            "processing_pipeline": default_pipeline_status(),
        }

    @staticmethod
    def _record_key(record: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(record.get("entity_id") or ""),
            str(record.get("source_document_id") or ""),
            str(record.get("document_type") or ""),
        )

    @staticmethod
    def _single_value(records: list[dict[str, Any]], key: str) -> str | None:
        values = {str(record.get(key)) for record in records if record.get(key) is not None}
        return next(iter(values)) if len(values) == 1 else None

    def _load_required(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required registry not found: {path}")
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise ValueError(f"Registry must contain a JSON object: {path}")
        return payload

    @staticmethod
    def _stable_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()

    def _stable_id(self, prefix: str, value: str) -> str:
        return f"{prefix}_{self._stable_hash(value)[:20]}"

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _relative(self, path: Path) -> str:
        return str(path.relative_to(self.paths.project_root)).replace("\\", "/")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
