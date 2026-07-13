"""Durable, candidate-only work queue for document revalidation.

This module materializes document-change impact candidates as auditable work
items. It never extracts evidence, changes product facts, or changes product
identity records. Existing work-item decisions are preserved across rebuilds.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


REVALIDATION_WORK_QUEUE_VERSION = "1.0"
VALID_WORK_STATUSES = frozenset({"pending", "in_progress", "resolved", "dismissed"})
TERMINAL_WORK_STATUSES = frozenset({"resolved", "dismissed"})


class RevalidationWorkQueue:
    """Create and manage durable revalidation work items from impact candidates."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def candidate_registry_path(self) -> Path:
        return self.base_dir / "registry" / "document_change_impact_candidates.json"

    @property
    def queue_registry_path(self) -> Path:
        return self.base_dir / "registry" / "revalidation_work_queue.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "revalidation_work_queue_report.json"

    def build(self) -> dict[str, Any]:
        """Materialize new candidates and preserve prior work-item state."""
        candidates = self._load_json(self.candidate_registry_path).get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("Impact candidate registry field 'candidates' must be a list.")

        existing_items = self._load_optional_queue_items()
        existing_by_id = {
            item["revalidation_work_item_id"]: item
            for item in existing_items
            if isinstance(item, dict) and isinstance(item.get("revalidation_work_item_id"), str)
        }

        items: list[dict[str, Any]] = []
        created = 0
        retained = 0
        skipped = 0
        for candidate in candidates:
            if not self._is_valid_candidate(candidate):
                skipped += 1
                continue
            work_item_id = self._work_item_id(candidate)
            existing = existing_by_id.get(work_item_id)
            if existing is not None:
                items.append(self._merge_existing_item(existing, candidate))
                retained += 1
            else:
                items.append(self._new_work_item(candidate, work_item_id))
                created += 1

        items.sort(key=lambda item: (item["status"] != "pending", item["created_at"], item["revalidation_work_item_id"]))
        registry = {
            "schema_version": "1.0",
            "queue_version": REVALIDATION_WORK_QUEUE_VERSION,
            "generated_at": self._utc_now(),
            "source_candidate_registry": self._relative_path(self.candidate_registry_path),
            "work_item_count": len(items),
            "work_items": items,
        }
        status_counts = Counter(item["status"] for item in items)
        report = {
            "queue_version": REVALIDATION_WORK_QUEUE_VERSION,
            "generated_at": self._utc_now(),
            "impact_candidates_scanned": len(candidates),
            "work_items_created": created,
            "work_items_retained": retained,
            "invalid_candidates_skipped": skipped,
            "work_item_count": len(items),
            "status_counts": {status: status_counts.get(status, 0) for status in sorted(VALID_WORK_STATUSES)},
            "registry_output": self._relative_path(self.queue_registry_path),
        }
        self._write_json(self.queue_registry_path, registry)
        self._write_json(self.report_path, report)
        return {"registry": registry, "report": report, "registry_path": self.queue_registry_path, "report_path": self.report_path}

    def update_status(self, *, work_item_id: str, status: str, note: str | None = None) -> dict[str, Any]:
        """Change a work-item status with a durable audit event."""
        normalized_status = status.strip().lower()
        if normalized_status not in VALID_WORK_STATUSES:
            allowed = ", ".join(sorted(VALID_WORK_STATUSES))
            raise ValueError(f"Unsupported status '{status}'. Allowed values: {allowed}.")
        registry = self._load_json(self.queue_registry_path)
        items = registry.get("work_items")
        if not isinstance(items, list):
            raise ValueError("Work queue field 'work_items' must be a list.")

        for item in items:
            if not isinstance(item, dict) or item.get("revalidation_work_item_id") != work_item_id:
                continue
            old_status = item.get("status")
            if old_status not in VALID_WORK_STATUSES:
                raise ValueError(f"Work item '{work_item_id}' has invalid current status.")
            event = {
                "changed_at": self._utc_now(),
                "from_status": old_status,
                "to_status": normalized_status,
            }
            if note and note.strip():
                event["note"] = note.strip()
            item["status"] = normalized_status
            item["updated_at"] = event["changed_at"]
            item.setdefault("status_history", []).append(event)
            self._write_json(self.queue_registry_path, registry)
            return item
        raise KeyError(f"Work item not found: {work_item_id}")

    @staticmethod
    def _is_valid_candidate(candidate: Any) -> bool:
        return (
            isinstance(candidate, dict)
            and candidate.get("status") == "revalidation_candidate"
            and candidate.get("candidate_only") is True
            and isinstance(candidate.get("document_change_impact_id"), str)
            and bool(candidate["document_change_impact_id"].strip())
        )

    @staticmethod
    def _work_item_id(candidate: dict[str, Any]) -> str:
        candidate_id = candidate["document_change_impact_id"].strip()
        digest = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:12]
        return f"rwq_{digest}"

    def _new_work_item(self, candidate: dict[str, Any], work_item_id: str) -> dict[str, Any]:
        created_at = self._utc_now()
        return {
            "revalidation_work_item_id": work_item_id,
            "status": "pending",
            "candidate_only": True,
            "created_at": created_at,
            "updated_at": created_at,
            "source_document_change_impact_id": candidate["document_change_impact_id"],
            "product_identity_id": candidate.get("product_identity_id"),
            "insurer_id": candidate.get("insurer_id"),
            "product_uin": candidate.get("product_uin"),
            "source_product_link_id": candidate.get("source_product_link_id"),
            "document_type": candidate.get("document_type"),
            "logical_document_path": candidate.get("logical_document_path"),
            "changed_document_url_key": candidate.get("changed_document_url_key"),
            "previous_sha256": candidate.get("previous_sha256"),
            "new_sha256": candidate.get("new_sha256"),
            "required_next_action": "re_run_evidence_extraction_and_validation",
            "guardrail": "No product fact, product identity, or knowledge asset is changed automatically.",
            "status_history": [{"changed_at": created_at, "from_status": None, "to_status": "pending", "note": "Materialized from document-change impact candidate."}],
        }

    def _merge_existing_item(self, existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        """Refresh source fields while preserving human work state and audit trail."""
        merged = self._new_work_item(candidate, existing["revalidation_work_item_id"])
        merged["status"] = existing.get("status", "pending")
        merged["created_at"] = existing.get("created_at", merged["created_at"])
        merged["updated_at"] = existing.get("updated_at", merged["updated_at"])
        merged["status_history"] = existing.get("status_history", merged["status_history"])
        return merged

    def _load_optional_queue_items(self) -> list[dict[str, Any]]:
        if not self.queue_registry_path.exists():
            return []
        payload = self._load_json(self.queue_registry_path)
        items = payload.get("work_items", [])
        if not isinstance(items, list):
            raise ValueError("Existing work queue field 'work_items' must be a list.")
        return items

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

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path)
