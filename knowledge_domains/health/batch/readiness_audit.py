"""Deterministic readiness audit for the P2 Health product batch pilot.

This module only reports observable readiness. It does not infer product identity,
create product facts, or alter source evidence.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR

READINESS_AUDIT_VERSION = "1.0"


class HealthBatchReadinessAudit:
    """Audit declared pilot candidates against existing evidence and pipeline outputs."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def pilot_config_path(self) -> Path:
        return self.base_dir / "registry" / "health_batch_pilot.json"

    @property
    def identity_registry_path(self) -> Path:
        return self.base_dir / "registry" / "product_identity_registry.json"

    @property
    def link_registry_path(self) -> Path:
        return self.base_dir / "registry" / "source_product_link_registry.json"

    @property
    def pdf_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_registry.json"

    @property
    def field_registry_path(self) -> Path:
        return self.base_dir / "knowledge_domains" / "health" / "field_registry" / "health_field_registry.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "health_batch_readiness_report.json"

    def build(self) -> dict[str, Any]:
        config = self._load_json(self.pilot_config_path)
        identities = self._load_json(self.identity_registry_path).get("identities", [])
        links = self._load_json(self.link_registry_path).get("links", [])
        pdf_by_hash = self._load_json(self.pdf_registry_path).get("by_hash", {})
        field_registry = self._load_json(self.field_registry_path)
        fields = field_registry.get("fields", [])

        identity_by_entity = self._index_identities(identities)
        links_by_identity = self._index_links(links)
        records = [
            self._audit_candidate(candidate, identity_by_entity, links_by_identity, pdf_by_hash, fields)
            for candidate in config.get("candidate_products", [])
            if isinstance(candidate, dict)
        ]
        records.sort(key=lambda item: item["entity_id"])
        counts = Counter(record["readiness_status"] for record in records)
        report = {
            "schema_version": "1.0",
            "audit_version": READINESS_AUDIT_VERSION,
            "generated_at": self._utc_now(),
            "pilot_name": config.get("pilot_name"),
            "candidate_count": len(records),
            "readiness_counts": {status: counts.get(status, 0) for status in ("ready_for_batch", "needs_identity", "needs_local_documents", "blocked")},
            "canonical_field_count": len(fields) if isinstance(fields, list) else 0,
            "candidates": records,
        }
        self._write_json(self.report_path, report)
        return {"report": report, "report_path": self.report_path}

    def _audit_candidate(
        self,
        candidate: dict[str, Any],
        identity_by_entity: dict[str, dict[str, Any]],
        links_by_identity: dict[str, list[dict[str, Any]]],
        pdf_by_hash: dict[str, Any],
        fields: list[dict[str, Any]],
    ) -> dict[str, Any]:
        entity_id = self._text(candidate.get("entity_id")) or ""
        insurer_id = self._text(candidate.get("insurer_id")) or ""
        source_urls = [url for url in candidate.get("source_urls", []) if isinstance(url, str) and url.strip()]
        identity = identity_by_entity.get(entity_id)
        identity_id = identity.get("product_identity_id") if identity else None
        product_dir = self.base_dir / "knowledge" / "health" / insurer_id / entity_id.split(":", 1)[-1]
        intelligence_path = product_dir / "intelligence" / "product_intelligence.json"
        parsed_dir = product_dir / "parsed"
        documents_dir = product_dir / "documents"
        local_document_count = len(list(documents_dir.glob("*.pdf"))) if documents_dir.exists() else 0
        parsed_document_count = len(list(parsed_dir.glob("*.json"))) if parsed_dir.exists() else 0
        linked_documents = links_by_identity.get(identity_id, []) if identity_id else []
        registry_documents = self._matching_registry_documents(pdf_by_hash, source_urls)
        blockers: list[str] = []
        if not registry_documents and local_document_count == 0:
            blockers.append("no_observed_product_documents")
        if not identity:
            blockers.append("product_identity_not_verified")
        if not intelligence_path.exists():
            blockers.append("product_intelligence_not_generated")
        if not parsed_document_count:
            blockers.append("parsed_documents_not_generated")

        if not blockers:
            readiness = "ready_for_batch"
        elif "product_identity_not_verified" in blockers and (registry_documents or local_document_count):
            readiness = "needs_identity"
        elif "no_observed_product_documents" in blockers:
            readiness = "needs_local_documents"
        else:
            readiness = "blocked"

        return {
            "entity_id": entity_id,
            "insurer_id": insurer_id,
            "product_name": self._text(candidate.get("product_name")),
            "selection_reason": self._text(candidate.get("selection_reason")),
            "source_urls": source_urls,
            "readiness_status": readiness,
            "blockers": blockers,
            "identity": {
                "status": identity.get("resolution_status") if identity else "unresolved",
                "product_identity_id": identity_id,
                "uin": identity.get("uin") if identity else None,
            },
            "evidence_inventory": {
                "local_document_count": local_document_count,
                "parsed_document_count": parsed_document_count,
                "product_intelligence_present": intelligence_path.exists(),
                "source_product_link_count": len(linked_documents),
                "download_registry_document_count": len(registry_documents),
                "download_registry_document_types": sorted({item.get("document_type") for item in registry_documents if item.get("document_type")}),
            },
            "field_pipeline": {
                "canonical_field_count": len(fields),
                "extractor_supported_field_count": sum(1 for field in fields if field.get("maturity") == "extractor_supported"),
            },
        }

    @staticmethod
    def _index_identities(identities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for identity in identities:
            if not isinstance(identity, dict):
                continue
            for entity_id in identity.get("entity_ids", []):
                if isinstance(entity_id, str) and entity_id:
                    index[entity_id] = identity
        return index

    @staticmethod
    def _index_links(links: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = {}
        for link in links:
            if isinstance(link, dict) and isinstance(link.get("product_identity_id"), str):
                index.setdefault(link["product_identity_id"], []).append(link)
        return index

    @staticmethod
    def _matching_registry_documents(pdf_by_hash: dict[str, Any], source_urls: list[str]) -> list[dict[str, Any]]:
        source_url_set = set(source_urls)
        matches: list[dict[str, Any]] = []
        for record in pdf_by_hash.values():
            if isinstance(record, dict) and record.get("source_page_url") in source_url_set:
                matches.append(record)
        return matches

    @staticmethod
    def _text(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

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
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
