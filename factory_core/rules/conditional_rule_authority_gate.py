"""Deterministic gate for promoting a verified conditional-rule artifact.

The gate is generic: it validates an already-produced shadow artifact and its
parity report. It does not understand copay, Health terminology, or product IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
import json


class ConditionalRuleAuthorityGateError(ValueError):
    """Raised when a shadow artifact is not eligible for authoritative publication."""


@dataclass(frozen=True, slots=True)
class ConditionalRuleAuthorityDecision:
    """Immutable certification result for one proposed authority promotion."""

    source_rules_path: Path
    parity_report_path: Path
    source_rules_sha256: str
    parity_report_sha256: str
    entity_id: str
    field: str
    schema_version: str
    rule_ids: tuple[str, ...]


class ConditionalRuleAuthorityGate:
    """Certify a shadow artifact only when its recorded parity gate is clean.

    The gate intentionally does not infer semantic parity itself. It verifies the
    persisted parity report, checks source/report identity consistency, confirms
    the shadow artifact contains only evidence-backed conditional rules, and
    returns a deterministic publication decision.
    """

    REQUIRED_REPORT_KEYS = (
        "legacy_only",
        "generic_only",
        "evidence_lineage_issues",
    )

    def certify(
        self,
        *,
        shadow_rules_path: str | Path,
        parity_report_path: str | Path,
        expected_field: str | None = None,
    ) -> ConditionalRuleAuthorityDecision:
        rules_path = Path(shadow_rules_path)
        report_path = Path(parity_report_path)
        rules = self._load_object(rules_path, label="shadow conditional-rule artifact")
        report = self._load_object(report_path, label="conditional-rule parity report")

        self._assert_eligible(rules=rules, report=report, expected_field=expected_field)
        rule_ids = self._extract_rule_ids(rules)
        return ConditionalRuleAuthorityDecision(
            source_rules_path=rules_path,
            parity_report_path=report_path,
            source_rules_sha256=self._sha256_file(rules_path),
            parity_report_sha256=self._sha256_file(report_path),
            entity_id=str(rules["entity_id"]),
            field=str(rules["field"]),
            schema_version=str(rules["schema_version"]),
            rule_ids=rule_ids,
        )

    def _assert_eligible(self, *, rules: dict[str, Any], report: dict[str, Any], expected_field: str | None) -> None:
        if rules.get("authority_mode") != "shadow_non_authoritative":
            raise ConditionalRuleAuthorityGateError(
                "Only an explicitly shadow_non_authoritative artifact may be promoted."
            )
        if rules.get("parity_passed") is not True:
            raise ConditionalRuleAuthorityGateError("Shadow conditional-rule artifact has not passed parity.")
        if report.get("parity_passed") is not True:
            raise ConditionalRuleAuthorityGateError("Parity report does not certify parity_passed=true.")
        if rules.get("entity_id") != report.get("entity_id") or rules.get("field") != report.get("field"):
            raise ConditionalRuleAuthorityGateError("Shadow artifact and parity report identify different entity/field values.")
        if expected_field is not None and rules.get("field") != expected_field:
            raise ConditionalRuleAuthorityGateError(
                f"Expected field={expected_field!r}; received field={rules.get('field')!r}."
            )
        if not isinstance(rules.get("schema_version"), str) or not rules["schema_version"].strip():
            raise ConditionalRuleAuthorityGateError("Shadow artifact requires a non-blank schema_version.")
        if not isinstance(rules.get("entity_id"), str) or not rules["entity_id"].strip():
            raise ConditionalRuleAuthorityGateError("Shadow artifact requires a non-blank entity_id.")
        if not isinstance(rules.get("field"), str) or not rules["field"].strip():
            raise ConditionalRuleAuthorityGateError("Shadow artifact requires a non-blank field.")

        payload = report.get("report")
        if not isinstance(payload, dict):
            raise ConditionalRuleAuthorityGateError("Parity report requires an object-valued 'report'.")
        for key in self.REQUIRED_REPORT_KEYS:
            value = payload.get(key)
            if not isinstance(value, list):
                raise ConditionalRuleAuthorityGateError(f"Parity report requires list '{key}'.")
            if value:
                raise ConditionalRuleAuthorityGateError(f"Parity report contains unresolved '{key}'.")

        source_triage_rules = rules.get("source_triage_path")
        source_triage_report = report.get("source_triage_path")
        if not source_triage_rules or source_triage_rules != source_triage_report:
            raise ConditionalRuleAuthorityGateError("Shadow artifact/report must reference the same legacy triage path.")

        rule_ids = self._extract_rule_ids(rules)
        if not rule_ids:
            raise ConditionalRuleAuthorityGateError("Cannot publish an empty conditional-rule artifact.")
        if len(rule_ids) != len(set(rule_ids)):
            raise ConditionalRuleAuthorityGateError("Conditional-rule artifact contains duplicate rule_ids.")

        for rule in rules.get("rules", []):
            if not isinstance(rule, dict):
                raise ConditionalRuleAuthorityGateError("Each published rule must be an object.")
            if rule.get("status") != "evidence_assembled_not_fact_extracted":
                raise ConditionalRuleAuthorityGateError(
                    "Only evidence_assembled_not_fact_extracted rules may be published."
                )
            if rule.get("unresolved_ambiguities"):
                raise ConditionalRuleAuthorityGateError("Rules with unresolved ambiguities cannot be published.")
            if "product_level_fact" in rule or "default_value" in rule:
                raise ConditionalRuleAuthorityGateError("Flattened product facts/default values are forbidden.")
            evidence = rule.get("evidence")
            if not isinstance(evidence, dict) or not isinstance(evidence.get("primary_evidence"), dict):
                raise ConditionalRuleAuthorityGateError("Every published rule requires primary evidence lineage.")

    @staticmethod
    def _extract_rule_ids(rules: dict[str, Any]) -> tuple[str, ...]:
        items = rules.get("rules")
        if not isinstance(items, list):
            raise ConditionalRuleAuthorityGateError("Shadow artifact requires a list-valued 'rules'.")
        ids: list[str] = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("rule_id"), str) or not item["rule_id"].strip():
                raise ConditionalRuleAuthorityGateError("Each rule requires a non-blank rule_id.")
            ids.append(item["rule_id"])
        return tuple(ids)

    @staticmethod
    def _load_object(path: Path, *, label: str) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"{label} was not found: {path}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConditionalRuleAuthorityGateError(f"{label} is not valid JSON: {path}") from exc
        if not isinstance(value, dict):
            raise ConditionalRuleAuthorityGateError(f"{label} must contain one JSON object.")
        return value

    @staticmethod
    def _sha256_file(path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()
