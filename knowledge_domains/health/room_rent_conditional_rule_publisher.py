"""Controlled publication for verified Health room-rent conditional rules."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


class RoomRentConditionalRulePublicationError(ValueError):
    """Raised when a room-rent shadow artifact is not eligible for publication."""


@dataclass(frozen=True, slots=True)
class RoomRentConditionalRulePublicationResult:
    authoritative_rules_path: Path
    publication_receipt_path: Path
    entity_id: str
    rule_ids: tuple[str, ...]


class RoomRentConditionalRulePublisher:
    """Promote only a clean, explicit-schedule-verified room-rent artifact."""

    VERSION = "1.0"
    OUTPUT_SCHEMA_VERSION = "1.0"
    VERIFICATION_MODE = "explicit_schedule_coverage_v1"
    EXPECTED_RULE_TYPES = {"room_category_constraint", "icu_room_rent_exception"}

    def publish_from_shadow(
        self,
        *,
        shadow_rules_path: str | Path,
        verification_report_path: str | Path,
        factory_dir: str | Path,
        legacy_triage_path: str | Path,
        expected_rule_count: int = 2,
    ) -> RoomRentConditionalRulePublicationResult:
        triage_path = Path(legacy_triage_path)
        triage_hash_before = self._sha256_file(triage_path)
        source = self._load_object(Path(shadow_rules_path), label="room-rent shadow artifact")
        report = self._load_object(Path(verification_report_path), label="room-rent verification report")
        self._assert_eligible(source=source, report=report, expected_rule_count=expected_rule_count)

        entity_id = str(source["entity_id"])
        rule_ids = tuple(rule["rule_id"] for rule in source["rules"])
        output_dir = Path(factory_dir) / "conditional_rules"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_entity = self._safe_entity(entity_id)
        rules_path = output_dir / f"{safe_entity}_room_rent_conditional_rules.json"
        receipt_path = output_dir / f"{safe_entity}_room_rent_conditional_rule_publication_receipt.json"

        payload = {
            "schema_version": self.OUTPUT_SCHEMA_VERSION,
            "publisher_version": self.VERSION,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "authority_mode": "authoritative_conditional_rules",
            "entity_id": entity_id,
            "field": "room_rent",
            "source_shadow_rules_path": str(shadow_rules_path),
            "source_shadow_rules_sha256": self._sha256_file(Path(shadow_rules_path)),
            "source_verification_report_path": str(verification_report_path),
            "source_verification_report_sha256": self._sha256_file(Path(verification_report_path)),
            "source_legacy_triage_path": str(triage_path),
            "source_legacy_triage_sha256": triage_hash_before,
            "verification_mode": self.VERIFICATION_MODE,
            "verification_passed": True,
            "rules": source["rules"],
            "unassembled_fragments": [],
            "skipped_fragment_ids": [],
            "notes": [
                "This is the authoritative room-rent conditional-rule artifact after explicit schedule-coverage verification.",
                "It records room-category entitlement and an ICU exception only.",
                "It does not calculate a room-rent deduction, a proportionate deduction, or final claim payment.",
            ],
        }
        self._atomic_write_json(rules_path, payload)
        triage_hash_after = self._sha256_file(triage_path)
        if triage_hash_before != triage_hash_after:
            raise RuntimeError("Room-rent triage changed during publication; publication aborted.")

        receipt = {
            "schema_version": self.OUTPUT_SCHEMA_VERSION,
            "publisher_version": self.VERSION,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "authority_mode": "authoritative_conditional_rules",
            "entity_id": entity_id,
            "field": "room_rent",
            "rule_ids": list(rule_ids),
            "authoritative_rules_path": str(rules_path),
            "source_shadow_rules_path": str(shadow_rules_path),
            "source_verification_report_path": str(verification_report_path),
            "source_legacy_triage_path": str(triage_path),
            "legacy_triage_immutable": True,
            "verification_mode": self.VERIFICATION_MODE,
            "verification_passed": True,
        }
        self._atomic_write_json(receipt_path, receipt)
        return RoomRentConditionalRulePublicationResult(
            authoritative_rules_path=rules_path,
            publication_receipt_path=receipt_path,
            entity_id=entity_id,
            rule_ids=rule_ids,
        )

    def _assert_eligible(self, *, source: dict[str, Any], report: dict[str, Any], expected_rule_count: int) -> None:
        if source.get("authority_mode") != "shadow_non_authoritative":
            raise RoomRentConditionalRulePublicationError("Only a shadow_non_authoritative artifact may be published.")
        if source.get("field") != "room_rent" or report.get("field") != "room_rent":
            raise RoomRentConditionalRulePublicationError("Room-rent publication requires field='room_rent'.")
        if source.get("entity_id") != report.get("entity_id"):
            raise RoomRentConditionalRulePublicationError("Shadow artifact and verification report identify different entities.")
        if source.get("source_triage_path") != report.get("source_triage_path"):
            raise RoomRentConditionalRulePublicationError("Shadow artifact/report must reference the same triage path.")
        if source.get("verification_mode") != self.VERIFICATION_MODE or report.get("verification_mode") != self.VERIFICATION_MODE:
            raise RoomRentConditionalRulePublicationError("Unexpected room-rent verification mode.")
        if source.get("verification_passed") is not True or report.get("verification_passed") is not True:
            raise RoomRentConditionalRulePublicationError("Room-rent verification has not passed.")
        verification = report.get("verification")
        if not isinstance(verification, dict):
            raise RoomRentConditionalRulePublicationError("Verification report requires a verification object.")
        for key in ("missing_rule_types", "unexpected_rule_types", "unassembled_fragment_ids", "skipped_decision_evidence_ids"):
            value = verification.get(key)
            if not isinstance(value, list) or value:
                raise RoomRentConditionalRulePublicationError(f"Verification report contains unresolved '{key}'.")
        rules = source.get("rules")
        if not isinstance(rules, list) or len(rules) != expected_rule_count:
            raise RoomRentConditionalRulePublicationError(
                f"Expected exactly {expected_rule_count} room-rent rules."
            )
        rule_ids: list[str] = []
        rule_types: set[str] = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise RoomRentConditionalRulePublicationError("Each room-rent rule must be an object.")
            rule_id = rule.get("rule_id")
            if not isinstance(rule_id, str) or not rule_id.strip():
                raise RoomRentConditionalRulePublicationError("Each room-rent rule requires a non-blank rule_id.")
            rule_ids.append(rule_id)
            rule_types.add(str(rule.get("rule_type") or ""))
            if rule.get("status") != "evidence_assembled_not_fact_extracted":
                raise RoomRentConditionalRulePublicationError("Only evidence-assembled rules may be published.")
            if rule.get("unresolved_ambiguities"):
                raise RoomRentConditionalRulePublicationError("Rules with unresolved ambiguities cannot be published.")
            evidence = rule.get("evidence")
            if not isinstance(evidence, dict) or not isinstance(evidence.get("primary_evidence"), dict):
                raise RoomRentConditionalRulePublicationError("Every published rule requires primary evidence.")
        if len(rule_ids) != len(set(rule_ids)):
            raise RoomRentConditionalRulePublicationError("Duplicate room-rent rule IDs are forbidden.")
        if rule_types != self.EXPECTED_RULE_TYPES:
            raise RoomRentConditionalRulePublicationError("Published room-rent rule types do not match the approved schedule contract.")

    @staticmethod
    def _load_object(path: Path, *, label: str) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"{label} was not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RoomRentConditionalRulePublicationError(f"{label} must contain one JSON object.")
        return payload

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, indent=2, ensure_ascii=False)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            handle.write(encoded)
            temporary = Path(handle.name)
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _safe_entity(entity_id: str) -> str:
        return entity_id.replace(":", "_").replace("/", "_").replace("\\", "_").lower()

    @staticmethod
    def _sha256_file(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Room-rent triage artifact was not found: {path}")
        return sha256(path.read_bytes()).hexdigest()
