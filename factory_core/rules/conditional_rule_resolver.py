"""Read-only resolver for published conditional-rule artifacts.

This module intentionally does not evaluate rules, calculate financial outcomes,
or generate advice. It validates and retrieves only already-published,
evidence-backed conditional rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
import json


class ConditionalRuleResolutionError(RuntimeError):
    """Raised when a published conditional-rule artifact is invalid or unusable."""


@dataclass(frozen=True, slots=True)
class ConditionalRuleQuery:
    """Optional deterministic filters for authoritative conditional rules."""

    concept_id: str | None = None
    rule_type: str | None = None
    entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class ConditionalRuleResolution:
    """Read-only result of resolving a published conditional-rule artifact."""

    entity_id: str
    field: str
    source_path: Path
    schema_version: str
    rules: tuple[Mapping[str, Any], ...]

    @property
    def rule_count(self) -> int:
        return len(self.rules)


class ConditionalRuleResolver:
    """Loads and filters an authoritative conditional-rule artifact.

    The resolver accepts only artifacts explicitly marked authoritative. It never
    reads shadow-mode output and never derives a product-level default value.
    """

    REQUIRED_TOP_LEVEL_KEYS = frozenset(
        {
            "schema_version",
            "entity_id",
            "field",
            "rules",
        }
    )

    def resolve(
        self,
        artifact_path: str | Path,
        query: ConditionalRuleQuery | None = None,
    ) -> ConditionalRuleResolution:
        path = Path(artifact_path)
        payload = self._load_payload(path)
        self._validate_payload(payload, path)

        query = query or ConditionalRuleQuery()
        entity_id = payload["entity_id"]
        if query.entity_id is not None and query.entity_id != entity_id:
            return ConditionalRuleResolution(
                entity_id=entity_id,
                field=payload["field"],
                source_path=path,
                schema_version=payload["schema_version"],
                rules=(),
            )

        rules = tuple(
            rule
            for rule in payload["rules"]
            if self._matches(rule, query)
        )
        return ConditionalRuleResolution(
            entity_id=entity_id,
            field=payload["field"],
            source_path=path,
            schema_version=payload["schema_version"],
            rules=rules,
        )

    def _load_payload(self, path: Path) -> Mapping[str, Any]:
        if not path.is_file():
            raise ConditionalRuleResolutionError(
                f"Authoritative conditional-rule artifact does not exist: {path}"
            )
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ConditionalRuleResolutionError(
                f"Conditional-rule artifact is not valid JSON: {path}"
            ) from exc
        if not isinstance(payload, dict):
            raise ConditionalRuleResolutionError(
                f"Conditional-rule artifact root must be an object: {path}"
            )
        return payload

    def _validate_payload(self, payload: Mapping[str, Any], path: Path) -> None:
        missing = self.REQUIRED_TOP_LEVEL_KEYS.difference(payload)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ConditionalRuleResolutionError(
                f"Conditional-rule artifact is missing required keys ({missing_text}): {path}"
            )

        authority_mode = payload.get("authority_mode")
        if authority_mode not in (None, "authoritative", "authoritative_conditional_rules"):
            raise ConditionalRuleResolutionError(
                "Conditional-rule resolver accepts authoritative artifacts only (including authoritative_conditional_rules); "
                f"received authority_mode={authority_mode!r}: {path}"
            )

        if not isinstance(payload["entity_id"], str) or not payload["entity_id"]:
            raise ConditionalRuleResolutionError(
                f"Conditional-rule artifact has invalid entity_id: {path}"
            )
        if not isinstance(payload["field"], str) or not payload["field"]:
            raise ConditionalRuleResolutionError(
                f"Conditional-rule artifact has invalid field: {path}"
            )
        if not isinstance(payload["rules"], list):
            raise ConditionalRuleResolutionError(
                f"Conditional-rule artifact rules must be a list: {path}"
            )

        seen_rule_ids: set[str] = set()
        for index, rule in enumerate(payload["rules"]):
            if not isinstance(rule, dict):
                raise ConditionalRuleResolutionError(
                    f"Rule at index {index} is not an object: {path}"
                )
            self._validate_rule(rule, index, path, seen_rule_ids)

    @staticmethod
    def _validate_rule(
        rule: Mapping[str, Any],
        index: int,
        path: Path,
        seen_rule_ids: set[str],
    ) -> None:
        required = {
            "rule_id",
            "concept_id",
            "rule_type",
            "effect",
            "applies_when",
            "coverage_scope",
            "evidence",
            "status",
        }
        missing = required.difference(rule)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ConditionalRuleResolutionError(
                f"Rule at index {index} is missing required keys ({missing_text}): {path}"
            )

        rule_id = rule["rule_id"]
        if not isinstance(rule_id, str) or not rule_id:
            raise ConditionalRuleResolutionError(
                f"Rule at index {index} has invalid rule_id: {path}"
            )
        if rule_id in seen_rule_ids:
            raise ConditionalRuleResolutionError(
                f"Rule artifact contains duplicate rule_id={rule_id!r}: {path}"
            )
        seen_rule_ids.add(rule_id)

        if rule.get("status") != "evidence_assembled_not_fact_extracted":
            raise ConditionalRuleResolutionError(
                f"Rule {rule_id!r} does not have an evidence-assembled status: {path}"
            )

        evidence = rule["evidence"]
        if not isinstance(evidence, dict) or not evidence.get("primary_evidence"):
            raise ConditionalRuleResolutionError(
                f"Rule {rule_id!r} has no primary evidence lineage: {path}"
            )

        ambiguities = rule.get("unresolved_ambiguities", [])
        if ambiguities:
            raise ConditionalRuleResolutionError(
                f"Rule {rule_id!r} has unresolved ambiguities and cannot be resolved: {path}"
            )

    @staticmethod
    def _matches(rule: Mapping[str, Any], query: ConditionalRuleQuery) -> bool:
        return (
            (query.concept_id is None or rule["concept_id"] == query.concept_id)
            and (query.rule_type is None or rule["rule_type"] == query.rule_type)
        )
