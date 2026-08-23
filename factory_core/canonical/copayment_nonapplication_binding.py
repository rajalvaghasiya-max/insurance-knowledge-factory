"""Governed binding for explicit conditional co-payment non-application rules.

The binding is deliberately separate from percentage-bearing co-payment obligations.
It reuses the generic legal-condition binder only for source/authority/candidate/hash
validation, then emits a refined non-application semantic manifest.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

from factory_core.canonical.generic_legal_condition_binding import (
    GenericLegalConditionBinding,
)
from insurance_intelligence.benefits.copayment_nonapplication import (
    ConditionalCopaymentNonapplication,
    CopaymentNonapplicationEffect,
)


class CopaymentNonapplicationBindingError(ValueError):
    """Raised when a reviewed non-application binding is incomplete or unsafe."""


@dataclass(frozen=True)
class CopaymentNonapplicationBindingResult:
    manifest: Mapping[str, Any]


_PERCENTAGE = re.compile(r"(?<!\d)\d{1,3}(?:\.\d+)?\s*%")
_NONAPPLICATION_SIGNAL = re.compile(
    r"\b(?:no\s+co-?payment\s+shall\s+apply|co-?payment\s+(?:does\s+not|shall\s+not|will\s+not)\s+apply)\b",
    re.I,
)


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CopaymentNonapplicationBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CopaymentNonapplicationBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CopaymentNonapplicationBindingError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise CopaymentNonapplicationBindingError(f"{label} must be repository-relative")
    return path.as_posix()


class CopaymentNonapplicationBinding:
    """Bind reviewed explicit non-application clauses without manufacturing 0%."""

    def bind_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
    ) -> CopaymentNonapplicationBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CopaymentNonapplicationBindingError(
                f"Invalid binding specification JSON: {path}"
            ) from exc
        return self.bind(spec=_mapping(spec, "binding_spec"), repository_root=repository_root)

    def bind(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
    ) -> CopaymentNonapplicationBindingResult:
        spec = _mapping(spec, "binding_spec")
        if spec.get("schema_version") != "1.0":
            raise CopaymentNonapplicationBindingError("binding_spec.schema_version must be 1.0")
        if spec.get("binding_type") != "copayment_nonapplication_binding_v1":
            raise CopaymentNonapplicationBindingError(
                "binding_spec.binding_type must be copayment_nonapplication_binding_v1"
            )
        if spec.get("reviewed_by_human") is not True:
            raise CopaymentNonapplicationBindingError("binding_spec.reviewed_by_human must be true")

        bundle_path = _safe_relative(
            spec.get("generic_source_bundle_path"), "generic_source_bundle_path"
        )
        rules = _items(spec.get("rules"), "binding_spec.rules")
        if not rules:
            raise CopaymentNonapplicationBindingError("binding_spec.rules must not be empty")

        translated_assertions: list[dict[str, Any]] = []
        typed_by_id: dict[str, ConditionalCopaymentNonapplication] = {}
        seen: set[str] = set()
        for index, raw_rule in enumerate(rules):
            rule = _mapping(raw_rule, f"rules[{index}]")
            rule_id = _text(rule.get("rule_id"), f"rules[{index}].rule_id")
            if rule_id in seen:
                raise CopaymentNonapplicationBindingError("rule_id values must be unique")
            seen.add(rule_id)
            semantic_key = _text(rule.get("semantic_key"), f"rules[{index}].semantic_key")
            statement = _text(
                rule.get("reviewed_statement"), f"rules[{index}].reviewed_statement"
            )
            if not _NONAPPLICATION_SIGNAL.search(statement):
                raise CopaymentNonapplicationBindingError(
                    f"{rule_id} must explicitly state that co-payment does not apply"
                )
            if _PERCENTAGE.search(statement):
                raise CopaymentNonapplicationBindingError(
                    f"{rule_id} must not encode non-application as a percentage value"
                )
            trigger = _text(
                rule.get("trigger_condition"), f"rules[{index}].trigger_condition"
            )
            scope = _text(
                rule.get("applicability_scope"), f"rules[{index}].applicability_scope"
            )
            selections = _items(
                rule.get("evidence_selections"), f"rules[{index}].evidence_selections"
            )
            if len(selections) != 1:
                raise CopaymentNonapplicationBindingError(
                    f"{rule_id} currently requires exactly one evidence selection"
                )
            selection = _mapping(selections[0], f"rules[{index}].evidence_selections[0]")
            candidate_id = _text(
                selection.get("candidate_id"), "evidence_selection.candidate_id"
            )
            typed_by_id[rule_id] = ConditionalCopaymentNonapplication(
                trigger_condition=trigger,
                applicability_scope=scope,
                evidence_reference_ids=(candidate_id,),
                effect=CopaymentNonapplicationEffect.DOES_NOT_APPLY,
            )
            translated_assertions.append(
                {
                    "assertion_id": rule_id,
                    "assertion_type": "conditional_copayment_rule",
                    "semantic_key": semantic_key,
                    "reviewed_statement": statement,
                    "evidence_selections": selections,
                }
            )

        validation_spec = {
            "schema_version": "1.0",
            "binding_type": "generic_legal_condition_binding_v1",
            "reviewed_by_human": True,
            "generic_source_bundle_path": bundle_path,
            "assertions": translated_assertions,
        }
        base_result = GenericLegalConditionBinding().bind(
            spec=validation_spec,
            repository_root=repository_root,
        )
        base_manifest = base_result.manifest
        base_assertions = {
            item["assertion_id"]: item for item in base_manifest["assertions"]
        }

        bound_rules: list[dict[str, Any]] = []
        for raw_rule in rules:
            rule = _mapping(raw_rule, "rule")
            rule_id = _text(rule.get("rule_id"), "rule.rule_id")
            typed = typed_by_id[rule_id]
            validated = base_assertions[rule_id]
            bound_rules.append(
                {
                    "rule_id": rule_id,
                    "rule_type": "conditional_copayment_nonapplication_rule",
                    "semantic_key": _text(rule.get("semantic_key"), "rule.semantic_key"),
                    "reviewed_statement": _text(
                        rule.get("reviewed_statement"), "rule.reviewed_statement"
                    ),
                    "semantic": {
                        "affected_cost_share": "COPAYMENT",
                        "effect": typed.effect.value,
                        "trigger_condition": typed.trigger_condition,
                        "applicability_scope": typed.applicability_scope,
                    },
                    "evidence": validated["evidence"],
                    "publication_status": "bound_not_published",
                }
            )

        return CopaymentNonapplicationBindingResult(
            manifest={
                "schema_version": "1.0",
                "binding_type": "copayment_nonapplication_binding_v1",
                "binding_status": "reviewed_copayment_nonapplication_bound_not_published",
                "product_context": base_manifest["product_context"],
                "generic_source_bundle_path": base_manifest["generic_source_bundle_path"],
                "generic_source_bundle_sha256": base_manifest[
                    "generic_source_bundle_sha256"
                ],
                "rules": bound_rules,
                "reviewed_by_human": True,
                "guardrails": [
                    "A definition-only co-payment mention cannot establish a product-level obligation or non-application rule.",
                    "Explicit non-application is not represented as a 0% positive co-payment obligation.",
                    "Binding does not authorize publication, comparison, decision support, or claim-payment inference.",
                ],
            }
        )

    def write_output(
        self,
        result: CopaymentNonapplicationBindingResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise CopaymentNonapplicationBindingError(
                "output_path must remain under repository_root"
            ) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(result.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target


__all__ = [
    "CopaymentNonapplicationBinding",
    "CopaymentNonapplicationBindingError",
    "CopaymentNonapplicationBindingResult",
]
