"""Read-only shadow assembly for reviewed Health room-rent schedule evidence.

Unlike copay, Room Rent has no legacy rule artifact to compare against yet.
This runner therefore records an explicit schedule-coverage verification instead
of claiming parity. It never mutates triage evidence and writes only shadow
artifacts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from factory_core.rules.conditional_rule_assembler import ConditionalRuleAssembler
from knowledge_domains.health.rule_parsers.room_rent_schedule_fragment_adapter import (
    RoomRentScheduleFragmentAdapter,
)


@dataclass(frozen=True, slots=True)
class RoomRentConditionalRuleShadowResult:
    conditional_rules_path: Path
    verification_report_path: Path
    verification_passed: bool
    rule_count: int
    unassembled_fragment_count: int


class RoomRentConditionalRuleShadowRunner:
    """Create non-authoritative room-rent rules from reviewed schedule triage."""

    VERSION = "1.0"
    OUTPUT_SCHEMA_VERSION = "1.0"
    VERIFICATION_MODE = "explicit_schedule_coverage_v1"
    EXPECTED_RULE_TYPES = (
        "room_category_constraint",
        "icu_room_rent_exception",
    )

    def __init__(
        self,
        *,
        adapter: RoomRentScheduleFragmentAdapter | None = None,
        assembler: ConditionalRuleAssembler | None = None,
    ) -> None:
        self._adapter = adapter or RoomRentScheduleFragmentAdapter()
        self._assembler = assembler or ConditionalRuleAssembler()

    def run_from_triage_file(
        self,
        *,
        triage_path: str | Path,
        factory_dir: str | Path,
    ) -> RoomRentConditionalRuleShadowResult:
        triage_file = Path(triage_path)
        triage = self._load_json(triage_file)
        return self.run_from_triage(
            triage=triage,
            factory_dir=factory_dir,
            source_triage_path=triage_file,
        )

    def run_from_triage(
        self,
        *,
        triage: dict[str, Any],
        factory_dir: str | Path,
        source_triage_path: str | Path | None = None,
    ) -> RoomRentConditionalRuleShadowResult:
        if str(triage.get("field") or "") != "room_rent":
            raise ValueError("RoomRentConditionalRuleShadowRunner only accepts field='room_rent' triage output.")

        adapted = self._adapter.adapt_triage(triage)
        assembly = self._assembler.assemble(adapted.fragments)
        observed_rule_types = tuple(sorted(rule.rule_type for rule in assembly.assembled_rules))
        expected_rule_types = tuple(sorted(self.EXPECTED_RULE_TYPES))
        missing = tuple(sorted(set(expected_rule_types) - set(observed_rule_types)))
        unexpected = tuple(sorted(set(observed_rule_types) - set(expected_rule_types)))
        unassembled_ids = tuple(sorted(fragment.fragment_id for fragment in assembly.unassembled_fragments))
        skipped = tuple(sorted(adapted.skipped_evidence_ids))
        verification_passed = not missing and not unexpected and not unassembled_ids and not skipped

        root = Path(factory_dir)
        output_dir = root / "conditional_rule_shadow"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_entity = self._safe_entity(str(triage.get("entity_id") or "unknown"))
        generated_at = datetime.now(timezone.utc).isoformat()
        source_reference = str(source_triage_path) if source_triage_path is not None else None

        rules_payload = {
            "schema_version": self.OUTPUT_SCHEMA_VERSION,
            "runner_version": self.VERSION,
            "generated_at": generated_at,
            "authority_mode": "shadow_non_authoritative",
            "entity_id": triage.get("entity_id"),
            "field": "room_rent",
            "source_triage_path": source_reference,
            "source_triage_schema_version": triage.get("schema_version"),
            "source_triage_version": triage.get("triage_version"),
            "verification_mode": self.VERIFICATION_MODE,
            "verification_passed": verification_passed,
            "rules": [rule.to_dict() for rule in assembly.assembled_rules],
            "unassembled_fragments": [fragment.to_dict() for fragment in assembly.unassembled_fragments],
            "skipped_fragment_ids": list(skipped),
            "notes": [
                "This is a derived shadow artifact. It is not an authoritative product fact.",
                "Room-rent publication is gated by explicit schedule coverage because no legacy room-rent rule artifact exists for parity comparison.",
                "No daily cap, proportionate deduction, or monetary claim outcome is created by this runner.",
            ],
        }
        report_payload = {
            "schema_version": self.OUTPUT_SCHEMA_VERSION,
            "runner_version": self.VERSION,
            "generated_at": generated_at,
            "authority_mode": "shadow_non_authoritative",
            "entity_id": triage.get("entity_id"),
            "field": "room_rent",
            "source_triage_path": source_reference,
            "verification_mode": self.VERIFICATION_MODE,
            "verification_passed": verification_passed,
            "verification": {
                "expected_rule_types": list(expected_rule_types),
                "observed_rule_types": list(observed_rule_types),
                "missing_rule_types": list(missing),
                "unexpected_rule_types": list(unexpected),
                "unassembled_fragment_ids": list(unassembled_ids),
                "skipped_decision_evidence_ids": list(skipped),
            },
        }

        rules_path = output_dir / f"{safe_entity}_room_rent_conditional_rules_shadow.json"
        report_path = output_dir / f"{safe_entity}_room_rent_conditional_rule_verification_report.json"
        self._write_json(rules_path, rules_payload)
        self._write_json(report_path, report_payload)
        return RoomRentConditionalRuleShadowResult(
            conditional_rules_path=rules_path,
            verification_report_path=report_path,
            verification_passed=verification_passed,
            rule_count=len(assembly.assembled_rules),
            unassembled_fragment_count=len(assembly.unassembled_fragments),
        )

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Room-rent triage artifact was not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Room-rent triage artifact must contain one JSON object.")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _safe_entity(entity_id: str) -> str:
        return entity_id.replace(":", "_").replace("/", "_").replace("\\", "_").lower()
