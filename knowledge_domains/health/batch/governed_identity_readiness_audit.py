"""P1.5b — read-only governed identity readiness audit.

Audits an explicitly declared portfolio of products against durable ProductIdentityReference
records and DocumentIdentityResolutionOverlay records. It does not register sources,
infer currentness, repair records, or publish insurance facts.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR

AUDIT_VERSION = "1.0"
_RECORD_TYPE = "product_identity_reference_v1"
_RECORD_STATUS = "reviewed_product_identity_recorded_not_published"
_OVERLAY_TYPE = "document_identity_resolution_overlay_v1"
_OVERLAY_STATUS = "reviewed_document_identity_resolution_recorded_not_published"

_STATUS_CURRENT_READY = "governed_current_entitlement_ready"
_STATUS_REVIEW_READY_BLOCKED = "governed_evidence_review_ready_current_entitlement_blocked"
_STATUS_LEGACY_MIGRATION = "legacy_governance_migration_required"
_STATUS_INCOMPLETE = "governance_incomplete"

_ALLOWED_STATUSES = (
    _STATUS_CURRENT_READY,
    _STATUS_REVIEW_READY_BLOCKED,
    _STATUS_LEGACY_MIGRATION,
    _STATUS_INCOMPLETE,
)


class GovernedIdentityReadinessAuditError(ValueError):
    """Raised when an explicit readiness scope is invalid or unsafe."""


class GovernedIdentityReadinessAudit:
    """Build a deterministic, non-mutating governance-readiness report."""

    def __init__(
        self,
        *,
        base_dir: Path | None = None,
        scope_path: str | Path = "registry/p1_5b_governed_identity_readiness_scope.json",
        report_path: str | Path = "reports/p1_5b_governed_identity_readiness_report.json",
    ) -> None:
        self.base_dir = (base_dir or BASE_DIR).resolve()
        self.scope_path = self._safe_path(scope_path, "scope_path")
        self.report_path = self._safe_path(report_path, "report_path")

    def build(self, *, generated_at: str | None = None) -> dict[str, Any]:
        scope = self._load_json(self.scope_path, "scope")
        if scope.get("schema_version") != "1.0":
            raise GovernedIdentityReadinessAuditError("scope.schema_version must be 1.0")
        if scope.get("scope_type") != "governed_identity_readiness_scope_v1":
            raise GovernedIdentityReadinessAuditError(
                "scope.scope_type must be governed_identity_readiness_scope_v1"
            )
        products = self._list(scope.get("products"), "scope.products")
        if not products:
            raise GovernedIdentityReadinessAuditError("scope.products must not be empty")

        seen_entities: set[str] = set()
        records: list[dict[str, Any]] = []
        for index, raw in enumerate(products):
            item = self._mapping(raw, f"scope.products[{index}]")
            entity_id = self._nonempty(item.get("entity_id"), f"scope.products[{index}].entity_id")
            if entity_id in seen_entities:
                raise GovernedIdentityReadinessAuditError("scope.products must not repeat entity_id")
            seen_entities.add(entity_id)
            records.append(self._audit_product(item, index=index))

        records.sort(key=lambda item: item["entity_id"])
        counts = Counter(item["governed_readiness_status"] for item in records)
        report = {
            "schema_version": "1.0",
            "audit_type": "governed_identity_readiness_audit_v1",
            "audit_version": AUDIT_VERSION,
            "audit_status": "read_only_observed_not_published",
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "scope_name": self._nonempty(scope.get("scope_name"), "scope.scope_name"),
            "product_count": len(records),
            "governed_readiness_counts": {status: counts.get(status, 0) for status in _ALLOWED_STATUSES},
            "products": records,
            "guardrails": [
                "This audit is read-only and does not create, change, or repair identity, source, classification, overlay, or publication artifacts.",
                "A durable product identity record establishes product identity only; it does not establish document-version compatibility.",
                "Only overlay decisions are reported for document current-entitlement eligibility; this audit does not infer currentness.",
                "Legacy lineage may be valuable, but it is not treated as equivalent to governed source registration and identity overlays.",
            ],
        }
        target = self.base_dir / self.report_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"report": report, "report_path": target}

    def _audit_product(self, item: dict[str, Any], *, index: int) -> dict[str, Any]:
        entity_id = self._nonempty(item.get("entity_id"), f"scope.products[{index}].entity_id")
        insurer_id = self._nonempty(item.get("insurer_id"), f"scope.products[{index}].insurer_id")
        product_id = self._nonempty(item.get("product_id"), f"scope.products[{index}].product_id")
        if entity_id != f"{insurer_id}:{product_id}":
            raise GovernedIdentityReadinessAuditError(
                f"scope.products[{index}].entity_id must equal insurer_id:product_id"
            )

        identity_path = self._optional_path(item.get("product_identity_reference_path"),
                                            f"scope.products[{index}].product_identity_reference_path")
        overlay_path = self._optional_path(item.get("document_identity_overlay_path"),
                                           f"scope.products[{index}].document_identity_overlay_path")
        legacy_lineage_path = self._optional_path(item.get("legacy_lineage_path"),
                                                   f"scope.products[{index}].legacy_lineage_path")
        blockers: list[str] = []
        identity = self._inspect_identity(identity_path, entity_id, blockers)
        overlay = self._inspect_overlay(overlay_path, entity_id, identity_path, blockers)

        if identity["present"] and overlay["present"] and overlay["current_eligible_document_count"] > 0:
            status = _STATUS_CURRENT_READY
        elif (
            identity["present"] and overlay["present"]
            and overlay["evidence_review_eligible_document_count"] > 0
            and overlay["current_eligible_document_count"] == 0
            and overlay["current_entitlement_blocked_document_count"] > 0
        ):
            status = _STATUS_REVIEW_READY_BLOCKED
        elif not identity["present"] and not overlay["present"] and legacy_lineage_path is not None:
            status = _STATUS_LEGACY_MIGRATION
            blockers.append("durable_product_identity_reference_missing")
            blockers.append("document_identity_overlay_missing")
        else:
            status = _STATUS_INCOMPLETE
            if not identity["present"]:
                blockers.append("durable_product_identity_reference_missing")
            if not overlay["present"]:
                blockers.append("document_identity_overlay_missing")

        return {
            "entity_id": entity_id,
            "insurer_id": insurer_id,
            "product_id": product_id,
            "product_name": self._nonempty(item.get("product_name"), f"scope.products[{index}].product_name"),
            "governed_readiness_status": status,
            "blockers": sorted(set(blockers)),
            "product_identity_reference": identity,
            "document_identity_overlay": overlay,
            "legacy_lineage": {
                "declared": legacy_lineage_path is not None,
                "path": legacy_lineage_path,
                "path_exists": bool(legacy_lineage_path and (self.base_dir / legacy_lineage_path).is_file()),
            },
        }

    def _inspect_identity(self, path: str | None, entity_id: str, blockers: list[str]) -> dict[str, Any]:
        if path is None:
            return {"present": False, "path": None, "record_sha256": None, "resolution_status": None, "uin": None}
        full = self.base_dir / path
        if not full.is_file():
            blockers.append("product_identity_reference_path_missing")
            return {"present": False, "path": path, "record_sha256": None, "resolution_status": None, "uin": None}
        record = self._load_json(path, "product_identity_reference")
        valid = (
            record.get("record_type") == _RECORD_TYPE
            and record.get("record_status") == _RECORD_STATUS
            and record.get("reviewed_by_human") is True
            and record.get("identity_resolution_status") == "resolved"
        )
        identity = record.get("product_identity")
        if not isinstance(identity, dict) or identity.get("entity_id") != entity_id:
            valid = False
            blockers.append("product_identity_reference_entity_mismatch")
        if not valid:
            blockers.append("product_identity_reference_invalid")
        return {
            "present": valid,
            "path": path,
            "record_sha256": self._sha256(full),
            "resolution_status": record.get("identity_resolution_status"),
            "uin": identity.get("uin") if isinstance(identity, dict) else None,
        }

    def _inspect_overlay(self, path: str | None, entity_id: str, identity_path: str | None, blockers: list[str]) -> dict[str, Any]:
        empty = {
            "present": False, "path": path, "record_sha256": None, "document_count": 0,
            "resolved_document_count": 0, "current_eligible_document_count": 0,
            "compatibility_unverified_document_count": 0,
            "evidence_review_eligible_document_count": 0,
            "current_entitlement_blocked_document_count": 0,
        }
        if path is None:
            return empty
        full = self.base_dir / path
        if not full.is_file():
            blockers.append("document_identity_overlay_path_missing")
            return empty
        record = self._load_json(path, "document_identity_overlay")
        valid = (
            record.get("overlay_type") == _OVERLAY_TYPE
            and record.get("overlay_status") == _OVERLAY_STATUS
            and record.get("reviewed_by_human") is True
        )
        product_ref = record.get("product_identity_reference")
        if not isinstance(product_ref, dict) or product_ref.get("entity_id") != entity_id:
            valid = False
            blockers.append("document_identity_overlay_entity_mismatch")
        if identity_path is not None and isinstance(product_ref, dict) and product_ref.get("identity_record_path") != identity_path:
            valid = False
            blockers.append("document_identity_overlay_identity_reference_mismatch")
        documents = record.get("documents")
        if not isinstance(documents, list):
            valid = False
            documents = []
            blockers.append("document_identity_overlay_documents_invalid")
        if not valid:
            blockers.append("document_identity_overlay_invalid")
        resolved = current_eligible = compatibility_unverified = evidence_eligible = entitlement_blocked = 0
        for raw in documents:
            if not isinstance(raw, dict):
                continue
            decision = raw.get("identity_resolution")
            if not isinstance(decision, dict):
                continue
            if decision.get("resolution_status") == "resolved":
                resolved += 1
            if decision.get("evidence_review_eligibility") == "eligible_for_evidence_review":
                evidence_eligible += 1
            if (
                decision.get("temporal_status") in {"current", "current_observed_reviewed"}
                and decision.get("current_entitlement_publication_eligibility") == "eligible"
            ):
                current_eligible += 1
            if decision.get("temporal_status") == "compatibility_unverified":
                compatibility_unverified += 1
            if decision.get("current_entitlement_publication_eligibility") == "blocked":
                entitlement_blocked += 1
        return {
            "present": valid,
            "path": path,
            "record_sha256": self._sha256(full),
            "document_count": len(documents),
            "resolved_document_count": resolved,
            "current_eligible_document_count": current_eligible,
            "compatibility_unverified_document_count": compatibility_unverified,
            "evidence_review_eligible_document_count": evidence_eligible,
            "current_entitlement_blocked_document_count": entitlement_blocked,
        }

    def _safe_path(self, value: str | Path, label: str) -> str:
        raw = self._nonempty(str(value), label)
        path = Path(raw)
        if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
            raise GovernedIdentityReadinessAuditError(f"{label} must be a safe repository-relative path")
        return path.as_posix()

    def _optional_path(self, value: Any, label: str) -> str | None:
        if value is None:
            return None
        return self._safe_path(value, label)

    def _load_json(self, relative_path: str, label: str) -> dict[str, Any]:
        path = (self.base_dir / relative_path).resolve()
        try:
            path.relative_to(self.base_dir)
        except ValueError as exc:
            raise GovernedIdentityReadinessAuditError(f"{label} must remain under base_dir") from exc
        if not path.is_file():
            raise GovernedIdentityReadinessAuditError(f"{label} was not found: {relative_path}")
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GovernedIdentityReadinessAuditError(f"{label} is not valid JSON: {relative_path}") from exc
        return self._mapping(parsed, label)

    @staticmethod
    def _mapping(value: Any, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise GovernedIdentityReadinessAuditError(f"{label} must be a JSON object")
        return value

    @staticmethod
    def _list(value: Any, label: str) -> list[Any]:
        if not isinstance(value, list):
            raise GovernedIdentityReadinessAuditError(f"{label} must be a JSON array")
        return value

    @staticmethod
    def _nonempty(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise GovernedIdentityReadinessAuditError(f"{label} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = __import__("hashlib").sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
