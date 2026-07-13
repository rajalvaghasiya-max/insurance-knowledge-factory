"""Adapter from legacy copay triage output to generic rule fragments.

This module is deliberately a read-only compatibility adapter.  It does not call
or modify ``CopayEvidenceTriage``.  It converts the evidence-rich output already
produced by that stage into ``ConditionalRuleFragment`` objects so that the new
core can be validated beside the live path before any migration.

It contains Health/copay vocabulary only.  Generic assembly and reconciliation
remain in ``factory_core``.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable

from factory_core.rules.conditional_rule_fragment_models import (
    ConditionalRuleFragment,
    FragmentCompleteness,
    FragmentProvenance,
    FragmentRole,
)
from factory_core.rules.conditional_rule_models import (
    ConditionOperator,
    EvidenceReference,
    RuleEffect,
    RuleEffectValueKind,
    RulePredicate,
)


@dataclass(frozen=True, slots=True)
class CopayFragmentAdaptationResult:
    """Read-only adapter output with conversion diagnostics."""

    fragments: tuple[ConditionalRuleFragment, ...]
    skipped_fragment_ids: tuple[str, ...]


class CopayFragmentAdapter:
    """Translate triaged Health copay evidence into generic rule fragments.

    The adapter never chooses a product-level copay, never invents a default
    claim route, and never merges evidence.  It only normalizes values and
    context explicitly carried by the triage output.
    """

    PARSER_ID = "health.copay_fragment_adapter"
    VERSION = "1.0"
    FIELD_PROFILE_ID = "health.copay.v1"

    def adapt_triage(self, triage: dict[str, Any]) -> CopayFragmentAdaptationResult:
        if str(triage.get("field") or "") != "copay":
            raise ValueError("CopayFragmentAdapter only accepts triage output for field='copay'.")

        fragments: list[ConditionalRuleFragment] = []
        skipped: list[str] = []
        for candidate in self._iter_candidates(triage):
            status = str(candidate.get("triage_status") or "")
            if status == "decision_bearing":
                for decision in candidate.get("decision_fragments") or ():
                    if not isinstance(decision, dict):
                        continue
                    adapted = self._adapt_decision_fragment(candidate, decision)
                    if adapted is None:
                        skipped.append(str(decision.get("fragment_id") or "unknown"))
                    else:
                        fragments.append(adapted)
            elif status == "supporting_context":
                fragments.append(self._adapt_supporting_context(candidate))

        return CopayFragmentAdaptationResult(
            fragments=tuple(sorted(fragments, key=lambda item: item.fragment_id)),
            skipped_fragment_ids=tuple(sorted(skipped)),
        )

    @staticmethod
    def _iter_candidates(triage: dict[str, Any]) -> Iterable[dict[str, Any]]:
        # Triage output preserves categories separately; accept a compact
        # test-friendly form as well without mutating it.
        for key in ("decision_bearing_candidates", "supporting_context_candidates"):
            for candidate in triage.get(key) or ():
                if isinstance(candidate, dict):
                    yield candidate

    def _adapt_decision_fragment(
        self,
        candidate: dict[str, Any],
        fragment: dict[str, Any],
    ) -> ConditionalRuleFragment | None:
        values = self._parse_percentages(fragment.get("percentages"))
        if not values:
            return None

        condition_labels = {str(value) for value in fragment.get("condition_labels") or ()}
        applies_when = self._conditions(condition_labels, fragment.get("coverage_context") or {})
        coverage_scope = self._scope(fragment.get("scope_context") or {}, fragment.get("coverage_context") or {})

        value_kind = (
            RuleEffectValueKind.ALLOWED_SET
            if "voluntary" in condition_labels and len(values) > 1
            else RuleEffectValueKind.FIXED
        )
        effect_value: int | float | tuple[int | float, ...]
        if value_kind is RuleEffectValueKind.ALLOWED_SET:
            effect_value = tuple(values)
        elif len(values) == 1:
            effect_value = values[0]
        else:
            # Multiple fixed percentages without a proven selectable-option
            # semantic are ambiguous and must not be guessed into a rule.
            return self._ambiguous_multi_value_fragment(candidate, fragment)

        return ConditionalRuleFragment(
            fragment_id=str(fragment["fragment_id"]),
            concept_id="copay",
            rule_type="cost_share",
            role=FragmentRole.RULE_CANDIDATE,
            completeness=FragmentCompleteness.COMPLETE,
            effect=RuleEffect(
                operator="insured_bears_percentage",
                value=effect_value,
                unit="percent",
                basis="admissible_claim_amount",
                value_kind=value_kind,
            ),
            applies_when=applies_when,
            coverage_scope=coverage_scope,
            evidence=self._evidence(candidate, fragment),
            provenance=self._provenance(),
            assembly_group_hint=self._group_hint(fragment),
            source_text_hash=self._source_text_hash(fragment),
        )

    def _adapt_supporting_context(self, candidate: dict[str, Any]) -> ConditionalRuleFragment:
        evidence_id = str(candidate.get("evidence_id") or "unknown")
        fragment_id = f"cpf_support_{sha256(evidence_id.encode('utf-8')).hexdigest()[:16]}"
        return ConditionalRuleFragment(
            fragment_id=fragment_id,
            concept_id="copay",
            rule_type="cost_share",
            role=FragmentRole.SUPPORTING_DEFINITION,
            completeness=FragmentCompleteness.SUPPORT_ONLY,
            evidence=self._evidence(candidate, {}),
            provenance=self._provenance(),
            source_text_hash=self._source_text_hash(candidate),
        )

    def _ambiguous_multi_value_fragment(
        self,
        candidate: dict[str, Any],
        fragment: dict[str, Any],
    ) -> ConditionalRuleFragment:
        return ConditionalRuleFragment(
            fragment_id=str(fragment["fragment_id"]),
            concept_id="copay",
            rule_type="cost_share",
            role=FragmentRole.UNRESOLVED,
            completeness=FragmentCompleteness.AMBIGUOUS,
            evidence=self._evidence(candidate, fragment),
            provenance=self._provenance(),
            assembly_group_hint=self._group_hint(fragment),
            source_text_hash=self._source_text_hash(fragment),
            unresolved_ambiguities=(
                "Multiple copay percentages were evidenced without an explicit selectable-option semantic.",
            ),
        )

    @staticmethod
    def _parse_percentages(raw_values: Any) -> list[int | float]:
        parsed: list[int | float] = []
        for raw in raw_values or ():
            text = str(raw).strip().rstrip("%").strip()
            try:
                number = float(text)
            except ValueError:
                continue
            if number < 0 or number > 100:
                continue
            parsed.append(int(number) if number.is_integer() else number)
        # Preserve source order while removing duplicates.
        return list(dict.fromkeys(parsed))

    @staticmethod
    def _conditions(labels: set[str], coverage: dict[str, Any]) -> tuple[RulePredicate, ...]:
        predicates: list[RulePredicate] = []
        if "voluntary" in labels:
            predicates.append(RulePredicate("cost_share_mode", ConditionOperator.EQUALS, "voluntary"))
        if "mandatory" in labels:
            predicates.append(RulePredicate("cost_share_mode", ConditionOperator.EQUALS, "mandatory"))

        claim_mode = str(coverage.get("claim_mode") or "")
        if claim_mode == "not_pre_approved_reimbursement":
            predicates.extend((
                RulePredicate("claim_route", ConditionOperator.EQUALS, "reimbursement"),
                RulePredicate("pre_approval_status", ConditionOperator.EQUALS, "not_pre_approved"),
            ))
        elif claim_mode == "pre_approved_reimbursement":
            predicates.extend((
                RulePredicate("claim_route", ConditionOperator.EQUALS, "reimbursement"),
                RulePredicate("pre_approval_status", ConditionOperator.EQUALS, "pre_approved"),
            ))
        elif claim_mode == "reimbursement_unspecified":
            predicates.append(RulePredicate("claim_route", ConditionOperator.EQUALS, "reimbursement"))
        return tuple(predicates)

    @staticmethod
    def _scope(scope_context: dict[str, Any], coverage: dict[str, Any]) -> tuple[RulePredicate, ...]:
        predicates: list[RulePredicate] = []
        for label in scope_context.get("scope_labels") or ():
            predicates.append(RulePredicate("health_scope", ConditionOperator.EQUALS, str(label)))
        for label in coverage.get("coverage_labels") or ():
            predicates.append(RulePredicate("health_cover", ConditionOperator.EQUALS, str(label)))
        return tuple(predicates)

    def _evidence(self, candidate: dict[str, Any], fragment: dict[str, Any]) -> EvidenceReference:
        evidence_id = str(candidate.get("evidence_id") or "unknown")
        document_id = str(candidate.get("document_id") or evidence_id)
        document_type = str(candidate.get("document_type") or candidate.get("source_type") or "unknown")
        authority = int(candidate.get("authority_score") or 0)
        char_range = fragment.get("source_char_range")
        valid_range = None
        if isinstance(char_range, dict) and {"start", "end"}.issubset(char_range):
            valid_range = {"start": int(char_range["start"]), "end": int(char_range["end"])}
        return EvidenceReference(
            evidence_id=evidence_id,
            document_id=document_id,
            document_type=document_type,
            authority_score=authority,
            fragment_id=str(fragment.get("fragment_id") or "") or None,
            source_char_range=valid_range,
        )

    def _provenance(self) -> FragmentProvenance:
        return FragmentProvenance(
            parser_id=self.PARSER_ID,
            parser_version=self.VERSION,
            field_profile_id=self.FIELD_PROFILE_ID,
        )

    @staticmethod
    def _source_text_hash(source: dict[str, Any]) -> str | None:
        text = str(source.get("text") or source.get("fragment_text") or "")
        return sha256(text.encode("utf-8")).hexdigest() if text else None

    @staticmethod
    def _group_hint(fragment: dict[str, Any]) -> str | None:
        text = str(fragment.get("text") or "")
        if not text:
            return None
        canonical = "".join(char for char in text.lower() if char.isalnum())
        return sha256(canonical.encode("utf-8")).hexdigest()[:24]
