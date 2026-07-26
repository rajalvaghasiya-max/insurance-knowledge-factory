"""Deterministic Product Identity ↔ Document Version linkage.

Links a verified Product Identity evidence reference to an immutable local file
fingerprint.  A PDF Download Registry record is attached only when the local
file SHA-256 is an exact match.  No filename, URL, document title, or product
slug matching is used as a fallback.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


SOURCE_PRODUCT_LINKAGE_VERSION = "1.0"


class ProvenanceStatus(StrEnum):
    DOWNLOAD_REGISTRY_VERIFIED = "download_registry_verified"
    LOCALLY_MANAGED_UNREGISTERED = "locally_managed_unregistered"
    LOCAL_FILE_MISSING = "local_file_missing"


class SourceProductLinkageBuilder:
    """Builds source-to-product links from verified identity evidence only."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def identity_registry_path(self) -> Path:
        return self.base_dir / "registry" / "product_identity_registry.json"

    @property
    def pdf_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_registry.json"

    @property
    def link_registry_path(self) -> Path:
        return self.base_dir / "registry" / "source_product_link_registry.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "source_product_linkage_report.json"

    def build(self) -> dict[str, Any]:
        identities = self._load_json(self.identity_registry_path).get("identities", [])
        pdf_by_hash = self._load_json(self.pdf_registry_path).get("by_hash", {})
        links = self._build_links(identities, pdf_by_hash)

        registry = {
            "schema_version": "1.0",
            "linkage_version": SOURCE_PRODUCT_LINKAGE_VERSION,
            "generated_at": self._utc_now(),
            "link_count": len(links),
            "links": links,
        }
        status_counts = Counter(link["provenance_status"] for link in links)
        report = {
            "linkage_version": SOURCE_PRODUCT_LINKAGE_VERSION,
            "generated_at": self._utc_now(),
            "identity_count_scanned": len(identities),
            "link_count": len(links),
            "provenance_status_counts": {
                status.value: status_counts.get(status.value, 0)
                for status in ProvenanceStatus
            },
            "registry_output": self._relative_path(self.link_registry_path),
        }

        self._write_json(self.link_registry_path, registry)
        self._write_json(self.report_path, report)
        return {
            "registry": registry,
            "report": report,
            "registry_path": self.link_registry_path,
            "report_path": self.report_path,
        }

    def _build_links(
        self,
        identities: list[dict[str, Any]],
        pdf_by_hash: dict[str, Any],
    ) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        seen: set[tuple[str, str, int | None, str | None]] = set()
        for identity in identities:
            if identity.get("resolution_status") != "verified":
                continue
            product_identity_id = self._required_text(identity, "product_identity_id")
            if not product_identity_id:
                continue
            for evidence in identity.get("evidence", []):
                if not isinstance(evidence, dict):
                    continue
                source = evidence.get("source")
                if not isinstance(source, dict):
                    continue
                source_file = self._required_text(source, "source_file")
                source_type = self._required_text(source, "source_type")
                page_number = source.get("page_number")
                dedupe_key = (product_identity_id, source_file or "", page_number, evidence.get("uin"))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                links.append(
                    self._make_link(
                        identity=identity,
                        evidence=evidence,
                        source_file=source_file,
                        source_type=source_type,
                        page_number=page_number,
                        pdf_by_hash=pdf_by_hash,
                    )
                )
        return sorted(links, key=lambda item: (item["product_identity_id"], item["logical_document_path"]))

    def _make_link(
        self,
        *,
        identity: dict[str, Any],
        evidence: dict[str, Any],
        source_file: str | None,
        source_type: str | None,
        page_number: Any,
        pdf_by_hash: dict[str, Any],
    ) -> dict[str, Any]:
        logical_path = source_file or ""
        local_path = self.base_dir / logical_path
        common = {
            "product_identity_id": identity["product_identity_id"],
            "insurer_id": identity.get("insurer_id"),
            "product_uin": identity.get("uin"),
            "relationship_status": "verified_identity_evidence",
            "link_method": "identity_resolution_evidence_fingerprint",
            "logical_document_path": logical_path,
            "document_type": source_type,
            "evidence_page_number": page_number,
            "uin_evidence": {
                "uin": evidence.get("uin"),
                "candidate_status": evidence.get("candidate_status"),
                "extraction_method": evidence.get("extraction_method"),
            },
        }
        if not source_file or not local_path.exists() or not local_path.is_file():
            return {
                **common,
                "source_product_link_id": self._link_id(identity["product_identity_id"], logical_path, "missing"),
                "document_sha256": None,
                "provenance_status": ProvenanceStatus.LOCAL_FILE_MISSING.value,
                "pdf_registry_record": None,
            }

        digest = self._sha256(local_path)
        registry_record = pdf_by_hash.get(digest)
        if isinstance(registry_record, dict):
            return {
                **common,
                "source_product_link_id": self._link_id(identity["product_identity_id"], logical_path, digest),
                "document_sha256": digest,
                "provenance_status": ProvenanceStatus.DOWNLOAD_REGISTRY_VERIFIED.value,
                "pdf_registry_record": self._registry_snapshot(registry_record),
            }
        return {
            **common,
            "source_product_link_id": self._link_id(identity["product_identity_id"], logical_path, digest),
            "document_sha256": digest,
            "provenance_status": ProvenanceStatus.LOCALLY_MANAGED_UNREGISTERED.value,
            "pdf_registry_record": None,
        }

    @staticmethod
    def _registry_snapshot(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "sha256": record.get("sha256"),
            "url": record.get("url"),
            "url_key": record.get("url_key"),
            "local_path": record.get("local_path"),
            "source_page_url": record.get("source_page_url"),
            "source_html_file": record.get("source_html_file"),
            "downloaded_at": record.get("downloaded_at"),
            "checked_at": record.get("checked_at"),
            "version_status": record.get("version_status"),
        }

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file_handle:
            for block in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _link_id(product_identity_id: str, logical_path: str, digest: str) -> str:
        value = f"{product_identity_id}:{logical_path}:{digest}"
        return f"spl_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"

    @staticmethod
    def _required_text(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required registry not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON registry: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Registry root must be an object: {path}")
        return payload

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
