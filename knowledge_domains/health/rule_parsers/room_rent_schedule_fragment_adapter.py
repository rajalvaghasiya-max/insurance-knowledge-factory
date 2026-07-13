"""Deterministic adapter for explicitly triaged Health room-rent schedule evidence.

This adapter is intentionally narrow. It does not parse arbitrary PDFs or infer
room-rent deductions. It converts *reviewed, explicit* schedule wording into
conditional-rule fragments that the generic assembler can consume.
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
    RulePredicate,
)
from knowledge_domains.health.room_category_taxonomy import normalize_room_category


@dataclass(frozen=True, slots=True)
class RoomRentFragmentAdaptationResult:
    fragments: tuple[ConditionalRuleFragment, ...]
    skipped_evidence_ids: tuple[str, ...]


class RoomRentScheduleFragmentAdapter:
    """Convert explicit schedule evidence into room-rent rule fragments.

    Supported reviewed patterns in this first release:
    * ``Room Rent: Single Private A.C room``
    * ``ICU: Up to S.I.``

    Anything else is deliberately skipped for later review. This is a bridge
    from triaged evidence to the reusable conditional-rule platform, not a
    general-purpose policy-language extractor.
    """

    PARSER_ID = "health.room_rent_schedule_fragment_adapter"
    VERSION = "1.0"
    FIELD_PROFILE_ID = "health.room_rent.v1"

    def adapt_triage(self, triage: dict[str, Any]) -> RoomRentFragmentAdaptationResult:
        if str(triage.get("field") or "") != "room_rent":
            raise ValueError("RoomRentScheduleFragmentAdapter only accepts field='room_rent'.")

        fragments: list[ConditionalRuleFragment] = []
        skipped: list[str] = []
        for item in self._iter_evidence(triage):
            text = self._canonical_text(str(item.get("text") or ""))

            extracted_fragments = []

            if "room rent:" in text:
                room_fragment = self._adapt_room_category(item, text)
                if room_fragment is not None:
                    extracted_fragments.append(room_fragment)

            if "icu:" in text:
                icu_fragment = self._adapt_icu_exception(item, text)
                if icu_fragment is not None:
                    extracted_fragments.append(icu_fragment)

            if extracted_fragments:
                fragments.extend(extracted_fragments)
            else:
                skipped.append(str(item.get("evidence_id") or "unknown"))

        return RoomRentFragmentAdaptationResult(
            fragments=tuple(sorted(fragments, key=lambda item: item.fragment_id)),
            skipped_evidence_ids=tuple(sorted(skipped)),
        )

    @staticmethod
    def _iter_evidence(triage: dict[str, Any]) -> Iterable[dict[str, Any]]:
        # A compact, reviewable triage contract for schedule excerpts.
        for item in triage.get("decision_bearing_candidates") or ():
            if isinstance(item, dict) and str(item.get("triage_status") or "") == "decision_bearing":
                yield item

    def _adapt_room_category(self, item: dict[str, Any], text: str) -> ConditionalRuleFragment | None:
        # Extract the schedule value after the exact label; do not use fuzzy or
        # partial matching because category labels can have financial impact.
        value = text.split("room rent:", 1)[1].split("icu:", 1)[0].strip(" .;,")
        category = normalize_room_category(value)
        if category is None:
            return None
        return self._fragment(
            item=item,
            suffix="room_category",
            rule_type="room_category_constraint",
            effect=RuleEffect(
                operator="selected_room_category_must_not_exceed",
                value=category.value,
                unit="room_category",
                basis="inpatient_hospitalisation",
            ),
            coverage_scope=(
                RulePredicate("health_scope", ConditionOperator.EQUALS, "inpatient_hospitalisation"),
            ),
        )

    def _adapt_icu_exception(self, item: dict[str, Any], text: str) -> ConditionalRuleFragment | None:
        # The first supported ICU pattern is explicit and non-numeric. It says
        # the ICU limit is up to Sum Insured, not that all claim costs are paid.
        if (
            "icu: up to s i" not in text
            and "icu: up to s.i" not in text
            and "icu: up to sum insured" not in text
        ):
            return None
        return self._fragment(
            item=item,
            suffix="icu_up_to_si",
            rule_type="icu_room_rent_exception",
            effect=RuleEffect(
                operator="room_rent_limit",
                value="up_to_sum_insured",
                unit="coverage_limit",
                basis="intensive_care_unit",
            ),
            applies_when=(
                RulePredicate("icu_stay", ConditionOperator.EQUALS, True),
            ),
            coverage_scope=(
                RulePredicate("health_scope", ConditionOperator.EQUALS, "intensive_care_unit"),
            ),
        )

    def _fragment(
        self,
        *,
        item: dict[str, Any],
        suffix: str,
        rule_type: str,
        effect: RuleEffect,
        applies_when: tuple[RulePredicate, ...] = (),
        coverage_scope: tuple[RulePredicate, ...] = (),
    ) -> ConditionalRuleFragment:
        evidence_id = str(item["evidence_id"])
        fragment_id = "rrf_" + sha256(f"{evidence_id}:{suffix}".encode("utf-8")).hexdigest()[:16]
        return ConditionalRuleFragment(
            fragment_id=fragment_id,
            concept_id="room_rent",
            rule_type=rule_type,
            role=FragmentRole.RULE_CANDIDATE,
            completeness=FragmentCompleteness.COMPLETE,
            effect=effect,
            applies_when=applies_when,
            coverage_scope=coverage_scope,
            evidence=EvidenceReference(
                evidence_id=evidence_id,
                document_id=str(item.get("document_id") or evidence_id),
                document_type=str(item.get("document_type") or "policy_schedule"),
                authority_score=int(item.get("authority_score") or 0),
                fragment_id=fragment_id,
                source_char_range=self._char_range(item.get("source_char_range")),
            ),
            provenance=FragmentProvenance(
                parser_id=self.PARSER_ID,
                parser_version=self.VERSION,
                field_profile_id=self.FIELD_PROFILE_ID,
            ),
            source_text_hash=sha256(str(item.get("text") or "").encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _char_range(value: Any) -> dict[str, int] | None:
        if isinstance(value, dict) and {"start", "end"}.issubset(value):
            return {"start": int(value["start"]), "end": int(value["end"])}
        return None

    @staticmethod
    def _canonical_text(value: str) -> str:
        return " ".join(value.lower().replace(".", " ").split())
