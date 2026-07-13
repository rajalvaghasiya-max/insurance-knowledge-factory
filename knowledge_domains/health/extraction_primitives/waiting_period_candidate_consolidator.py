from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Mapping


class WaitingPeriodCandidateConsolidationError(ValueError):
    """Raised when waiting-period evidence-candidate input is malformed."""


class WaitingPeriodCandidateConsolidator:
    """Consolidate waiting-period evidence candidates without creating facts.

    The consolidator is deliberately evidence-only. It groups identical category/
    duration candidates, preserves every supporting occurrence, and emits review
    flags for repeated, schedule-like, option-like, or service-scoped wording.
    It does not select a product value, resolve applicability, or publish facts.
    """

    SCHEMA_VERSION = "1.0"
    VERSION = "1.0"
    PRIMITIVE_NAME = "waiting_period_candidate_consolidator"

    _SCHEDULE_OR_OPTION_RE = re.compile(
        r"\b(?:plan\s*\d+|options?\s+available|change\s+in|will\s+decrease|policy\s+schedule|sum\s+insured|\bSI\b)\b",
        re.IGNORECASE,
    )
    _SERVICE_SCOPE_RE = re.compile(
        r"\b(?:tele[-\s]?consultation|consultation|investigations?|preventive\s+health(?:\s+check[-\s]?up)?)\b",
        re.IGNORECASE,
    )

    def consolidate(self, candidate_document: Mapping[str, Any]) -> dict[str, Any]:
        source, candidates = self._validate(candidate_document)
        by_group: dict[tuple[str, int, str], list[Mapping[str, Any]]] = defaultdict(list)
        by_category: dict[str, set[tuple[int, str]]] = defaultdict(set)

        for candidate in candidates:
            category, value, unit = self._candidate_key(candidate)
            by_group[(category, value, unit)].append(candidate)
            by_category[category].add((value, unit))

        groups = [
            self._build_group(source, key, occurrences, by_category[key[0]])
            for key, occurrences in by_group.items()
        ]
        groups.sort(key=lambda item: (item["waiting_period_category"], item["duration"]["normalized_months"] is None, item["duration"]["normalized_months"] or 0, item["duration"]["value"]))

        return {
            "schema_version": self.SCHEMA_VERSION,
            "primitive": self.PRIMITIVE_NAME,
            "primitive_version": self.VERSION,
            "status": "candidates_consolidated" if groups else "no_candidates_to_consolidate",
            "source": dict(source),
            "input_candidate_count": len(candidates),
            "consolidated_group_count": len(groups),
            "groups": groups,
            "limitations": [
                "Consolidated groups are evidence-review work items only; they are not canonical facts or publication decisions.",
                "A repeated duration does not prove product-wide applicability.",
                "Schedule, option, service-scope, table layout, reading-order, and currentness decisions remain outside this primitive.",
            ],
        }

    def _build_group(
        self,
        source: Mapping[str, Any],
        key: tuple[str, int, str],
        occurrences: list[Mapping[str, Any]],
        category_durations: set[tuple[int, str]],
    ) -> dict[str, Any]:
        category, value, unit = key
        pages = sorted({self._page_number(item) for item in occurrences})
        evidence_texts = [self._evidence_text(item) for item in occurrences]
        flags: list[str] = []
        if len(occurrences) > 1:
            flags.append("repeated_same_duration")
        if len(pages) > 1:
            flags.append("repeated_across_pages")
        if any(self._SCHEDULE_OR_OPTION_RE.search(text) for text in evidence_texts):
            flags.append("schedule_or_option_layout_possible")
        if any(self._SERVICE_SCOPE_RE.search(text) for text in evidence_texts):
            flags.append("benefit_or_service_scoped_possible")
        if len(category_durations) > 1:
            flags.append("multiple_distinct_durations_for_category")
        if not flags:
            flags.append("single_explicit_candidate")

        sha256 = str(source.get("sha256") or "unknown")
        stable = "|".join((sha256, category, str(value), unit))
        group_id = f"wpgroup_{hashlib.sha256(stable.encode('utf-8')).hexdigest()[:16]}"
        normalized_months = value if unit == "months" else value * 12 if unit == "years" else None

        return {
            "group_id": group_id,
            "waiting_period_category": category,
            "duration": {
                "value": value,
                "unit": unit,
                "raw_value": self._raw_duration(value, unit),
                "normalized_months": normalized_months,
            },
            "occurrence_count": len(occurrences),
            "page_numbers": pages,
            "applicability_state": "unresolved_review_required",
            "review_flags": flags,
            "supporting_candidates": [self._occurrence_summary(item) for item in sorted(occurrences, key=lambda i: (self._page_number(i), str(i.get("candidate_id"))))],
            "non_fact_guardrail": "consolidated_evidence_candidate_only",
        }

    @staticmethod
    def _raw_duration(value: int, unit: str) -> str:
        singular = {"days": "day", "months": "month", "years": "year"}[unit]
        return f"{value} {singular if value == 1 else unit}"

    @staticmethod
    def _candidate_key(candidate: Mapping[str, Any]) -> tuple[str, int, str]:
        attributes = candidate.get("attributes")
        normalized_value = candidate.get("normalized_value")
        if not isinstance(attributes, Mapping):
            raise WaitingPeriodCandidateConsolidationError("candidate.attributes must be an object")
        if not isinstance(normalized_value, Mapping):
            raise WaitingPeriodCandidateConsolidationError("candidate.normalized_value must be an object")
        category = attributes.get("waiting_period_category")
        value = normalized_value.get("value")
        unit = normalized_value.get("unit")
        if normalized_value.get("kind") != "duration":
            raise WaitingPeriodCandidateConsolidationError("candidate.normalized_value.kind must be duration")
        if not isinstance(category, str) or not category:
            raise WaitingPeriodCandidateConsolidationError("candidate.attributes.waiting_period_category must be a non-empty string")
        if not isinstance(value, int) or value <= 0:
            raise WaitingPeriodCandidateConsolidationError("candidate.normalized_value.value must be a positive integer")
        if unit not in {"days", "months", "years"}:
            raise WaitingPeriodCandidateConsolidationError("candidate.normalized_value.unit must be days, months, or years")
        return category, value, unit

    @staticmethod
    def _page_number(candidate: Mapping[str, Any]) -> int:
        evidence = candidate.get("evidence")
        if not isinstance(evidence, Mapping) or not isinstance(evidence.get("page_number"), int):
            raise WaitingPeriodCandidateConsolidationError("candidate.evidence.page_number must be an integer")
        return evidence["page_number"]

    @staticmethod
    def _evidence_text(candidate: Mapping[str, Any]) -> str:
        evidence = candidate.get("evidence")
        if not isinstance(evidence, Mapping) or not isinstance(evidence.get("text"), str):
            raise WaitingPeriodCandidateConsolidationError("candidate.evidence.text must be a string")
        return evidence["text"]

    def _occurrence_summary(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        evidence = candidate["evidence"]
        confidence = candidate.get("confidence") if isinstance(candidate.get("confidence"), Mapping) else {}
        return {
            "candidate_id": candidate.get("candidate_id"),
            "page_number": evidence.get("page_number"),
            "evidence_text": evidence.get("text"),
            "confidence_score": confidence.get("score"),
            "requires_review": confidence.get("requires_review", True),
        }

    @staticmethod
    def _validate(candidate_document: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
        if candidate_document.get("primitive") != "waiting_period_duration_parser":
            raise WaitingPeriodCandidateConsolidationError("input primitive must be waiting_period_duration_parser")
        source = candidate_document.get("source")
        candidates = candidate_document.get("candidates")
        if not isinstance(source, Mapping):
            raise WaitingPeriodCandidateConsolidationError("input source must be an object")
        if not isinstance(candidates, list):
            raise WaitingPeriodCandidateConsolidationError("input candidates must be a list")
        if not all(isinstance(item, Mapping) for item in candidates):
            raise WaitingPeriodCandidateConsolidationError("input candidates must contain objects")
        return source, list(candidates)
