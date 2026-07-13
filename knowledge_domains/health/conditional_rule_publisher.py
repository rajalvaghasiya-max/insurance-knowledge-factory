"""Controlled publisher for Health conditional-rule artifacts.

This module promotes a certified generic shadow artifact to an authoritative
conditional-rule output. It never mutates legacy evidence-triage artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import os
import tempfile

from factory_core.rules.conditional_rule_authority_gate import (
    ConditionalRuleAuthorityDecision,
    ConditionalRuleAuthorityGate,
)


@dataclass(frozen=True, slots=True)
class ConditionalRulePublicationResult:
    """Immutable receipt for one authoritative Health publication."""

    authoritative_rules_path: Path
    publication_receipt_path: Path
    entity_id: str
    field: str
    rule_ids: tuple[str, ...]


class HealthConditionalRulePublisher:
    """Publish certified Health rules without altering legacy evidence artifacts."""

    VERSION = "1.0"
    OUTPUT_SCHEMA_VERSION = "1.0"

    def __init__(self, *, authority_gate: ConditionalRuleAuthorityGate | None = None) -> None:
        self._authority_gate = authority_gate or ConditionalRuleAuthorityGate()

    def publish_from_shadow(
        self,
        *,
        shadow_rules_path: str | Path,
        parity_report_path: str | Path,
        factory_dir: str | Path,
        legacy_triage_path: str | Path,
        expected_rule_count: int | None = None,
    ) -> ConditionalRulePublicationResult:
        """Certify and publish a generic Health rule artifact atomically.

        `legacy_triage_path` is hashed before and after publication to prove that
        this authority switch did not mutate the legacy evidence output.
        """
        triage_path = Path(legacy_triage_path)
        triage_hash_before = self._sha256_file(triage_path)
        decision = self._authority_gate.certify(
            shadow_rules_path=shadow_rules_path,
            parity_report_path=parity_report_path,
            expected_field="copay",
        )
        if expected_rule_count is not None and len(decision.rule_ids) != expected_rule_count:
            raise ValueError(
                f"Expected {expected_rule_count} authoritative rules; received {len(decision.rule_ids)}."
            )

        source = self._load_object(Path(shadow_rules_path), label="shadow conditional-rule artifact")
        output_dir = Path(factory_dir) / "conditional_rules"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_entity = self._safe_entity(decision.entity_id)
        rules_path = output_dir / f"{safe_entity}_{decision.field}_conditional_rules.json"
        receipt_path = output_dir / f"{safe_entity}_{decision.field}_conditional_rule_publication_receipt.json"

        payload = self._authoritative_payload(source=source, decision=decision, legacy_triage_path=triage_path)
        self._atomic_write_json(rules_path, payload)
        triage_hash_after = self._sha256_file(triage_path)
        if triage_hash_before != triage_hash_after:
            raise RuntimeError("Legacy evidence-triage artifact changed during authority publication; publication aborted.")

        receipt = {
            "schema_version": self.OUTPUT_SCHEMA_VERSION,
            "publisher_version": self.VERSION,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "authority_mode": "authoritative_conditional_rules",
            "entity_id": decision.entity_id,
            "field": decision.field,
            "rule_ids": list(decision.rule_ids),
            "authoritative_rules_path": str(rules_path),
            "source_shadow_rules_path": str(decision.source_rules_path),
            "source_shadow_rules_sha256": decision.source_rules_sha256,
            "source_parity_report_path": str(decision.parity_report_path),
            "source_parity_report_sha256": decision.parity_report_sha256,
            "source_legacy_triage_path": str(triage_path),
            "source_legacy_triage_sha256": triage_hash_before,
            "legacy_triage_immutable": True,
            "parity_passed": True,
            "notes": [
                "This receipt authorizes only the conditional-rule artifact.",
                "Legacy evidence triage remains preserved as immutable source evidence and compatibility reference.",
                "No flattened product-level copay default or absence claim is created.",
            ],
        }
        self._atomic_write_json(receipt_path, receipt)
        return ConditionalRulePublicationResult(
            authoritative_rules_path=rules_path,
            publication_receipt_path=receipt_path,
            entity_id=decision.entity_id,
            field=decision.field,
            rule_ids=decision.rule_ids,
        )

    def _authoritative_payload(
        self,
        *,
        source: dict[str, Any],
        decision: ConditionalRuleAuthorityDecision,
        legacy_triage_path: Path,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.OUTPUT_SCHEMA_VERSION,
            "publisher_version": self.VERSION,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "authority_mode": "authoritative_conditional_rules",
            "entity_id": decision.entity_id,
            "field": decision.field,
            "source_shadow_rules_path": str(decision.source_rules_path),
            "source_shadow_rules_sha256": decision.source_rules_sha256,
            "source_parity_report_path": str(decision.parity_report_path),
            "source_parity_report_sha256": decision.parity_report_sha256,
            "source_legacy_triage_path": str(legacy_triage_path),
            "source_legacy_triage_schema_version": source.get("source_triage_schema_version"),
            "source_legacy_triage_version": source.get("source_triage_version"),
            "parity_passed": True,
            "rules": source["rules"],
            "unassembled_fragments": source.get("unassembled_fragments", []),
            "skipped_fragment_ids": source.get("skipped_fragment_ids", []),
            "notes": [
                "This is the authoritative conditional-rule artifact after parity-gated publication.",
                "It is not a flattened product-level copay fact and does not imply customer option selection.",
                "Legacy evidence triage remains immutable source evidence and compatibility reference.",
            ],
        }

    @staticmethod
    def _load_object(path: Path, *, label: str) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"{label} was not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{label} must contain one JSON object.")
        return payload

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, indent=2, ensure_ascii=False)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
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
            raise FileNotFoundError(f"Legacy evidence-triage artifact was not found: {path}")
        return sha256(path.read_bytes()).hexdigest()
