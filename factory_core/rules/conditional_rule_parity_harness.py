"""Read-only parity harness for a legacy triage path and generic rule assembly.

This module is intentionally a certification aid, not production routing logic.
It does not modify legacy triage artifacts. It projects both outputs into a
common semantic fingerprint and reports every mismatch explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from factory_core.rules.conditional_rule_assembler import ConditionalRuleAssembler
from factory_core.rules.conditional_rule_models import ConditionalRule
from knowledge_domains.health.rule_parsers.copay_fragment_adapter import CopayFragmentAdapter


@dataclass(frozen=True, slots=True)
class ConditionalRuleParityReport:
    """Immutable result of one read-only legacy-versus-core comparison."""

    legacy_rule_fingerprints: tuple[tuple[object, ...], ...]
    generic_rule_fingerprints: tuple[tuple[object, ...], ...]
    legacy_only: tuple[tuple[object, ...], ...]
    generic_only: tuple[tuple[object, ...], ...]
    evidence_lineage_issues: tuple[str, ...]
    unassembled_fragment_ids: tuple[str, ...]

    @property
    def is_semantically_equivalent(self) -> bool:
        return not self.legacy_only and not self.generic_only and not self.evidence_lineage_issues


class CopayAssemblyParityHarness:
    """Compare legacy copay assemblies against generic core output.

    The harness intentionally treats a mismatch as a finding, not as a reason to
    coerce output. In particular, it must reveal unsupported reconciliation
    behaviour before the live path is migrated.
    """

    def __init__(
        self,
        adapter: CopayFragmentAdapter | None = None,
        assembler: ConditionalRuleAssembler | None = None,
    ) -> None:
        self._adapter = adapter or CopayFragmentAdapter()
        self._assembler = assembler or ConditionalRuleAssembler()

    def compare(self, triage: dict[str, Any]) -> ConditionalRuleParityReport:
        if str(triage.get("field") or "") != "copay":
            raise ValueError("CopayAssemblyParityHarness only accepts triage output for field='copay'.")

        adapted = self._adapter.adapt_triage(triage)
        generic = self._assembler.assemble(adapted.fragments)

        legacy_by_fingerprint = {
            self._legacy_fingerprint(assembly): assembly
            for assembly in triage.get("clause_assemblies") or ()
            if isinstance(assembly, dict)
        }
        generic_by_fingerprint = {
            self._generic_fingerprint(rule): rule
            for rule in generic.assembled_rules
        }

        legacy_keys = set(legacy_by_fingerprint)
        generic_keys = set(generic_by_fingerprint)
        shared = legacy_keys & generic_keys
        lineage_issues: list[str] = []
        for fingerprint in sorted(shared, key=repr):
            legacy = legacy_by_fingerprint[fingerprint]
            generated = generic_by_fingerprint[fingerprint]
            legacy_primary = str((legacy.get("primary_evidence") or {}).get("evidence_id") or "")
            generic_primary = generated.evidence.primary.evidence_id
            if legacy_primary and legacy_primary != generic_primary:
                lineage_issues.append(
                    f"Primary evidence mismatch for {fingerprint!r}: legacy={legacy_primary}, generic={generic_primary}."
                )

        return ConditionalRuleParityReport(
            legacy_rule_fingerprints=tuple(sorted(legacy_keys, key=repr)),
            generic_rule_fingerprints=tuple(sorted(generic_keys, key=repr)),
            legacy_only=tuple(sorted(legacy_keys - generic_keys, key=repr)),
            generic_only=tuple(sorted(generic_keys - legacy_keys, key=repr)),
            evidence_lineage_issues=tuple(sorted(lineage_issues)),
            unassembled_fragment_ids=tuple(item.fragment_id for item in generic.unassembled_fragments),
        )

    @staticmethod
    def _legacy_fingerprint(assembly: dict[str, Any]) -> tuple[object, ...]:
        values = tuple(_normalise_numeric(value) for value in assembly.get("percentages") or ())
        labels = tuple(sorted(str(value) for value in assembly.get("condition_labels") or ()))
        scope: list[tuple[str, str]] = []
        for label in assembly.get("scope_labels") or ():
            scope.append(("health_scope", str(label)))
        for label in assembly.get("coverage_labels") or ():
            scope.append(("health_cover", str(label)))

        applies: list[tuple[str, str]] = []
        if "voluntary" in labels:
            applies.append(("cost_share_mode", "voluntary"))
        if "mandatory" in labels:
            applies.append(("cost_share_mode", "mandatory"))
        claim_mode = str(assembly.get("claim_mode") or "")
        if claim_mode == "not_pre_approved_reimbursement":
            applies.extend((("claim_route", "reimbursement"), ("pre_approval_status", "not_pre_approved")))
        elif claim_mode == "pre_approved_reimbursement":
            applies.extend((("claim_route", "reimbursement"), ("pre_approval_status", "pre_approved")))
        elif claim_mode == "reimbursement_unspecified":
            applies.append(("claim_route", "reimbursement"))

        value_kind = "allowed_set" if "voluntary" in labels and len(values) > 1 else "fixed"
        effect_value: object = values if value_kind == "allowed_set" else values[0] if len(values) == 1 else values
        return (
            "copay",
            "cost_share",
            "insured_bears_percentage",
            value_kind,
            effect_value,
            "percent",
            "admissible_claim_amount",
            tuple(sorted(applies)),
            tuple(sorted(scope)),
        )

    @staticmethod
    def _generic_fingerprint(rule: ConditionalRule) -> tuple[object, ...]:
        return (
            rule.concept_id,
            rule.rule_type,
            rule.effect.operator,
            rule.effect.value_kind.value,
            rule.effect.value,
            rule.effect.unit,
            rule.effect.basis,
            tuple(sorted((item.dimension, str(item.value)) for item in rule.applies_when)),
            tuple(sorted((item.dimension, str(item.value)) for item in rule.coverage_scope)),
        )


def _normalise_numeric(value: object) -> int | float | str:
    text = str(value).strip().rstrip("%").strip()
    try:
        parsed = float(text)
    except ValueError:
        return text
    return int(parsed) if parsed.is_integer() else parsed
