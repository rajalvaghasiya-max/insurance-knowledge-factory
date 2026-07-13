"""Read-only shadow-mode integration for generic conditional-rule assembly.

This module consumes a *persisted legacy copay triage artifact* and writes only
new shadow artifacts. It never overwrites evidence triage or routing-plan output,
and the generic result is explicitly non-authoritative until a later controlled
authority switch is approved.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from factory_core.rules.conditional_rule_assembler import ConditionalRuleAssembler
from factory_core.rules.conditional_rule_parity_harness import (
    ConditionalRuleParityReport,
    CopayAssemblyParityHarness,
)
from knowledge_domains.health.rule_parsers.copay_fragment_adapter import CopayFragmentAdapter
from knowledge_domains.health.scope_reconciliation import HealthScopeReconciliationPolicy


@dataclass(frozen=True, slots=True)
class CopayConditionalRuleShadowResult:
    """Paths and certification status for one non-authoritative shadow run."""

    conditional_rules_path: Path
    parity_report_path: Path
    parity_passed: bool
    rule_count: int
    unassembled_fragment_count: int


class CopayConditionalRuleShadowRunner:
    """Build non-authoritative generic copay artifacts from legacy triage JSON.

    The legacy triage file is the source input and remains authoritative. A
    mismatch is recorded in the parity report; this runner must never coerce a
    mismatch or replace a legacy output.
    """

    VERSION = "1.0"
    OUTPUT_SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        *,
        adapter: CopayFragmentAdapter | None = None,
        assembler: ConditionalRuleAssembler | None = None,
        parity_harness: CopayAssemblyParityHarness | None = None,
    ) -> None:
        self._adapter = adapter or CopayFragmentAdapter()
        self._assembler = assembler or ConditionalRuleAssembler(
            scope_policy=HealthScopeReconciliationPolicy(),
        )
        self._parity_harness = parity_harness or CopayAssemblyParityHarness(
            adapter=self._adapter,
            assembler=self._assembler,
        )

    def run_from_triage_file(
        self,
        *,
        triage_path: str | Path,
        factory_dir: str | Path,
    ) -> CopayConditionalRuleShadowResult:
        """Load a persisted legacy triage artifact and write shadow-only outputs."""
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
    ) -> CopayConditionalRuleShadowResult:
        """Run generic assembly beside a legacy triage payload without mutation."""
        if str(triage.get("field") or "") != "copay":
            raise ValueError("CopayConditionalRuleShadowRunner only accepts field='copay' triage output.")

        adapted = self._adapter.adapt_triage(triage)
        assembly = self._assembler.assemble(adapted.fragments)
        parity = self._parity_harness.compare(triage)

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
            "field": "copay",
            "source_triage_path": source_reference,
            "source_triage_schema_version": triage.get("schema_version"),
            "source_triage_version": triage.get("triage_version"),
            "parity_passed": parity.is_semantically_equivalent,
            "rules": [rule.to_dict() for rule in assembly.assembled_rules],
            "unassembled_fragments": [fragment.to_dict() for fragment in assembly.unassembled_fragments],
            "skipped_fragment_ids": list(adapted.skipped_fragment_ids),
            "notes": [
                "This is a derived shadow artifact. It is not an authoritative product fact or replacement for legacy triage.",
                "A parity failure is recorded explicitly and does not change legacy artifacts.",
                "No product-level copay default or absence claim is created by this runner.",
            ],
        }
        report_payload = {
            "schema_version": self.OUTPUT_SCHEMA_VERSION,
            "runner_version": self.VERSION,
            "generated_at": generated_at,
            "authority_mode": "shadow_non_authoritative",
            "entity_id": triage.get("entity_id"),
            "field": "copay",
            "source_triage_path": source_reference,
            "parity_passed": parity.is_semantically_equivalent,
            "report": self._parity_to_dict(parity),
        }

        rules_path = output_dir / f"{safe_entity}_copay_conditional_rules_shadow.json"
        report_path = output_dir / f"{safe_entity}_copay_conditional_rule_parity_report.json"
        self._write_json(rules_path, rules_payload)
        self._write_json(report_path, report_payload)

        return CopayConditionalRuleShadowResult(
            conditional_rules_path=rules_path,
            parity_report_path=report_path,
            parity_passed=parity.is_semantically_equivalent,
            rule_count=len(assembly.assembled_rules),
            unassembled_fragment_count=len(assembly.unassembled_fragments),
        )

    @staticmethod
    def _parity_to_dict(report: ConditionalRuleParityReport) -> dict[str, Any]:
        return {
            "legacy_rule_fingerprints": [list(item) for item in report.legacy_rule_fingerprints],
            "generic_rule_fingerprints": [list(item) for item in report.generic_rule_fingerprints],
            "legacy_only": [list(item) for item in report.legacy_only],
            "generic_only": [list(item) for item in report.generic_only],
            "evidence_lineage_issues": list(report.evidence_lineage_issues),
            "unassembled_fragment_ids": list(report.unassembled_fragment_ids),
        }

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Legacy triage artifact was not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Legacy triage artifact must contain one JSON object.")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _safe_entity(entity_id: str) -> str:
        return entity_id.replace(":", "_").replace("/", "_").replace("\\", "_").lower()
