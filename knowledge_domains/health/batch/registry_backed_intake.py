"""Non-destructive intake planning for PDF-registry-backed Health product evidence."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR

INTAKE_VERSION = "1.0"


class RegistryBackedProductIntake:
    """Create deterministic evidence-intake plans without copying or modifying raw PDFs.

    Raw archived documents remain the evidence authority. This component only creates
    a governed relationship from a declared pilot product to exact PDF-registry entries.
    """

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def pilot_config_path(self) -> Path:
        return self.base_dir / "registry" / "health_batch_pilot.json"

    @property
    def pdf_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_registry.json"

    @property
    def registry_path(self) -> Path:
        return self.base_dir / "registry" / "product_evidence_intake_registry.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "product_evidence_intake_report.json"

    def build(self, *, entity_id: str) -> dict[str, Any]:
        candidate = self._candidate_for(entity_id)
        pdf_by_hash = self._load_json(self.pdf_registry_path).get("by_hash", {})
        expected_types = set(candidate.get("expected_document_types", []))
        source_urls = {value for value in candidate.get("source_urls", []) if isinstance(value, str) and value.strip()}

        records: list[dict[str, Any]] = []
        for sha256, record in pdf_by_hash.items():
            if not isinstance(record, dict):
                continue
            if record.get("insurer_id") != candidate.get("insurer_id"):
                continue
            if record.get("source_page_url") not in source_urls:
                continue
            document_type = record.get("document_type")
            if document_type not in expected_types:
                continue
            records.append(self._build_record(candidate, sha256, record))

        records.sort(key=lambda item: (self._document_rank(item.get("document_type")), item["document_type"], item["sha256"]))
        counts = Counter(item["intake_status"] for item in records)
        report = {
            "schema_version": "1.0",
            "intake_version": INTAKE_VERSION,
            "generated_at": self._utc_now(),
            "entity_id": entity_id,
            "insurer_id": candidate.get("insurer_id"),
            "product_name": candidate.get("product_name"),
            "source_urls": sorted(source_urls),
            "expected_document_types": sorted(expected_types),
            "intake_count": len(records),
            "status_counts": {
                "ready_for_processing": counts.get("ready_for_processing", 0),
                "blocked_missing_archive_file": counts.get("blocked_missing_archive_file", 0),
            },
            "records": records,
            "notes": [
                "Raw PDFs are not copied, renamed, or modified by intake.",
                "Each record is anchored to the immutable PDF SHA-256 recorded by the PDF Download Registry.",
                "This is an intake plan only; it does not publish facts or alter product identity.",
            ],
        }
        registry = self._load_existing_registry()
        existing = [item for item in registry.get("records", []) if isinstance(item, dict) and item.get("entity_id") != entity_id]
        registry = {
            "schema_version": "1.0",
            "intake_version": INTAKE_VERSION,
            "generated_at": self._utc_now(),
            "records": sorted(existing + records, key=lambda item: (item.get("entity_id", ""), item.get("document_type", ""), item.get("sha256", ""))),
        }
        self._write_json(self.registry_path, registry)
        self._write_json(self.report_path, report)
        return {"report": report, "report_path": self.report_path, "registry_path": self.registry_path}

    def _candidate_for(self, entity_id: str) -> dict[str, Any]:
        config = self._load_json(self.pilot_config_path)
        for candidate in config.get("candidate_products", []):
            if isinstance(candidate, dict) and candidate.get("entity_id") == entity_id:
                return candidate
        raise ValueError(f"Entity is not registered in the target Health batch: {entity_id}")

    def _build_record(self, candidate: dict[str, Any], sha256: str, record: dict[str, Any]) -> dict[str, Any]:
        relative_archive_path = self._relative_archive_path(record.get("local_path"))
        local_path = self.base_dir / relative_archive_path if relative_archive_path else None
        local_exists = bool(local_path and local_path.is_file())
        document_type = str(record.get("document_type") or "unknown")
        return {
            "intake_id": self._stable_id("pei", f"{candidate['entity_id']}|{sha256}|{document_type}"),
            "entity_id": candidate["entity_id"],
            "insurer_id": candidate.get("insurer_id"),
            "product_name": candidate.get("product_name"),
            "document_type": document_type,
            "evidence_role": self._evidence_role(document_type),
            "authority_score": self._authority_score(document_type),
            "provenance_status": "download_registry_verified",
            "source_document_id": f"sha256:{sha256}",
            "sha256": sha256,
            "source_url": record.get("url"),
            "source_page_url": record.get("source_page_url"),
            "captured_local_path": record.get("local_path"),
            "relative_archive_path": relative_archive_path,
            "local_file_exists": local_exists,
            "downloaded_at": record.get("downloaded_at"),
            "checked_at": record.get("checked_at") or record.get("last_checked_at"),
            "version_status": record.get("version_status"),
            "intake_status": "ready_for_processing" if local_exists else "blocked_missing_archive_file",
        }

    @staticmethod
    def _relative_archive_path(local_path: Any) -> str | None:
        if not isinstance(local_path, str) or not local_path.strip():
            return None
        normalized = local_path.replace("\\", "/")
        marker = "/archive/"
        if marker not in normalized:
            return None
        return "archive/" + normalized.split(marker, 1)[1]

    @staticmethod
    def _evidence_role(document_type: str) -> str:
        return {
            "policy_wording": "legal_authority",
            "customer_information_sheet": "regulatory_summary",
            "prospectus": "product_disclosure",
            "brochure": "marketing_disclosure",
            "proposal_form": "proposal_disclosure",
        }.get(document_type, "source_evidence")

    @staticmethod
    def _authority_score(document_type: str) -> int:
        return {
            "policy_wording": 100,
            "customer_information_sheet": 90,
            "prospectus": 75,
            "brochure": 60,
            "proposal_form": 50,
        }.get(document_type, 30)

    @staticmethod
    def _document_rank(document_type: Any) -> int:
        return {"policy_wording": 1, "customer_information_sheet": 2, "prospectus": 3, "brochure": 4, "proposal_form": 5}.get(str(document_type), 99)

    def _load_existing_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"records": []}
        return self._load_json(self.registry_path)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required JSON file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSON root must be an object: {path}")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _stable_id(prefix: str, value: str) -> str:
        return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
