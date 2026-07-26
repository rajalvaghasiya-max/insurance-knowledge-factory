"""Build non-publishing execution contracts for revalidation work items.

This module turns queue items into deterministic, auditable plans.  It does not
execute extraction, routing, validation, or publication.  Raw source evidence
remains authoritative; all derived outputs are explicitly reprocessable.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


REVALIDATION_EXECUTION_CONTRACT_VERSION = "1.0"
PLANNABLE_QUEUE_STATUSES = frozenset({"pending", "in_progress"})


class RevalidationExecutionContractBuilder:
    """Build immutable-input, non-publishing revalidation execution plans."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def queue_registry_path(self) -> Path:
        return self.base_dir / "registry" / "revalidation_work_queue.json"

    @property
    def identity_registry_path(self) -> Path:
        return self.base_dir / "registry" / "product_identity_registry.json"

    @property
    def source_link_registry_path(self) -> Path:
        return self.base_dir / "registry" / "source_product_link_registry.json"

    @property
    def contract_registry_path(self) -> Path:
        return self.base_dir / "registry" / "revalidation_execution_contracts.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "revalidation_execution_contract_report.json"

    def build(self) -> dict[str, Any]:
        """Create deterministic plans for non-terminal queue items only."""
        queue_items = self._load_json(self.queue_registry_path).get("work_items", [])
        identities = self._load_json(self.identity_registry_path).get("identities", [])
        links = self._load_json(self.source_link_registry_path).get("links", [])
        if not all(isinstance(value, list) for value in (queue_items, identities, links)):
            raise ValueError("Queue, identity, and source-link registry collections must be lists.")

        identities_by_id = {
            item.get("product_identity_id"): item
            for item in identities
            if isinstance(item, dict) and isinstance(item.get("product_identity_id"), str)
        }
        links_by_id = {
            item.get("source_product_link_id"): item
            for item in links
            if isinstance(item, dict) and isinstance(item.get("source_product_link_id"), str)
        }

        contracts: list[dict[str, Any]] = []
        skipped = 0
        for item in queue_items:
            if not self._is_plannable_item(item):
                skipped += 1
                continue
            identity = identities_by_id.get(item.get("product_identity_id"))
            link = links_by_id.get(item.get("source_product_link_id"))
            contracts.append(self._build_contract(item=item, identity=identity, link=link))

        contracts.sort(key=lambda item: item["revalidation_execution_contract_id"])
        status_counts = Counter(contract["execution_readiness"] for contract in contracts)
        registry = {
            "schema_version": "1.0",
            "execution_contract_version": REVALIDATION_EXECUTION_CONTRACT_VERSION,
            "generated_at": self._utc_now(),
            "non_publishing": True,
            "contract_count": len(contracts),
            "contracts": contracts,
        }
        report = {
            "execution_contract_version": REVALIDATION_EXECUTION_CONTRACT_VERSION,
            "generated_at": self._utc_now(),
            "queue_items_scanned": len(queue_items),
            "contracts_created": len(contracts),
            "queue_items_skipped": skipped,
            "readiness_counts": {key: status_counts.get(key, 0) for key in ("ready", "blocked")},
            "publication_allowed": False,
            "registry_output": self._relative_path(self.contract_registry_path),
        }
        self._write_json(self.contract_registry_path, registry)
        self._write_json(self.report_path, report)
        return {
            "registry": registry,
            "report": report,
            "registry_path": self.contract_registry_path,
            "report_path": self.report_path,
        }

    def _build_contract(
        self,
        *,
        item: dict[str, Any],
        identity: dict[str, Any] | None,
        link: dict[str, Any] | None,
    ) -> dict[str, Any]:
        work_item_id = self._required_text(item, "revalidation_work_item_id") or ""
        contract_id = self._contract_id(work_item_id, self._required_text(item, "new_sha256") or "")
        entity_ids = identity.get("entity_ids", []) if isinstance(identity, dict) else []
        valid_entity_ids = sorted({value.strip() for value in entity_ids if isinstance(value, str) and value.strip()})
        local_document_path = self._required_text(link or {}, "logical_document_path") or self._required_text(item, "logical_document_path")
        local_document_exists = bool(local_document_path and (self.base_dir / local_document_path).is_file())

        blockers: list[str] = []
        if identity is None:
            blockers.append("product_identity_missing")
        if link is None:
            blockers.append("source_product_link_missing")
        if len(valid_entity_ids) != 1:
            blockers.append("entity_scope_not_unique")
        if not local_document_path:
            blockers.append("logical_document_path_missing")
        elif not local_document_exists:
            blockers.append("logical_document_missing")

        entity_id = valid_entity_ids[0] if len(valid_entity_ids) == 1 else None
        readiness = "ready" if not blockers else "blocked"
        evidence = {
            "logical_document_path": local_document_path,
            "document_sha256": (link or {}).get("document_sha256") or item.get("previous_sha256"),
            "new_observed_sha256": item.get("new_sha256"),
            "provenance_status": (link or {}).get("provenance_status"),
            "source_product_link_id": item.get("source_product_link_id"),
            "local_document_exists": local_document_exists,
        }
        return {
            "revalidation_execution_contract_id": contract_id,
            "source_revalidation_work_item_id": work_item_id,
            "execution_readiness": readiness,
            "blockers": blockers,
            "candidate_only": True,
            "publication_allowed": False,
            "guardrail": "This contract may reprocess evidence and derive review outputs, but may not publish or overwrite product facts automatically.",
            "product_identity_id": item.get("product_identity_id"),
            "entity_id": entity_id,
            "source_evidence": evidence,
            "required_stages": self._required_stages(entity_id=entity_id),
            "review_decision_required": True,
        }

    @staticmethod
    def _required_stages(*, entity_id: str | None) -> list[dict[str, Any]]:
        stages: list[dict[str, Any]] = [
            {"stage": "preserve_source_version", "mode": "verify_only", "automatic_publication": False},
            {"stage": "parse_source_document", "mode": "reprocess", "automatic_publication": False},
            {"stage": "extract_product_intelligence", "mode": "reprocess", "automatic_publication": False},
            {"stage": "route_evidence", "mode": "reprocess", "automatic_publication": False},
            {"stage": "validate_product_intelligence", "mode": "reprocess", "automatic_publication": False},
            {"stage": "compare_derived_outputs", "mode": "review_package", "automatic_publication": False},
            {"stage": "human_review_decision", "mode": "manual", "automatic_publication": False},
        ]
        if entity_id:
            for stage in stages:
                stage["entity_id"] = entity_id
        return stages

    @staticmethod
    def _is_plannable_item(item: Any) -> bool:
        return (
            isinstance(item, dict)
            and item.get("candidate_only") is True
            and item.get("status") in PLANNABLE_QUEUE_STATUSES
            and isinstance(item.get("revalidation_work_item_id"), str)
            and bool(item["revalidation_work_item_id"].strip())
        )

    @staticmethod
    def _contract_id(work_item_id: str, new_sha256: str) -> str:
        value = f"{work_item_id}:{new_sha256}"
        return f"rec_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"

    @staticmethod
    def _required_text(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required JSON registry not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON registry: {path}") from exc
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

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path)
