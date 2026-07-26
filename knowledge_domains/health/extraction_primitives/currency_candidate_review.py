"""Reviewer-ready consolidation for currency evidence candidates.

This layer remains upstream of facts.  It groups deterministic monetary evidence
leads, surfaces contradictory/weak role cues, and asks a human reviewer to
resolve the meaning and applicability of the evidence.  It never promotes a
candidate into a canonical product field.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
import re
from typing import Any, Mapping

from .extraction_candidate_contract import ExtractionCandidateContract


class CurrencyCandidateReviewError(ValueError):
    """Raised when the candidate document is outside the review-layer contract."""


class CurrencyCandidateReview:
    VERSION = "1.0"
    REVIEW_TYPE = "health_currency_candidate_review_document_v1"

    _BENEFIT_LIMIT_TERMS = (
        "family visit", "air lift", "airlift", "maternity", "sub-limit",
        "sub limit", "limit for", "up to", "upto", "cover", "benefit",
    )

    # These labels are deliberately a small, deterministic review aid — not an
    # ontology or fact resolver.  They are extracted from text before the
    # monetary amount so a later benefit heading cannot re-label the amount.
    _SCOPE_LABELS = (
        ("family_visit", "family visit"),
        ("airlift", "air lift"),
        ("airlift", "airlift"),
        ("maternity", "maternity"),
        ("doctor_consultation", "doctor consultation"),
        ("general_physician_consultation", "general physician"),
        ("specialist_consultation", "specialists"),
        ("wellness_discount", "wellness discount"),
        ("minimum_premium", "minimum premium"),
    )

    def review(self, candidate_document: Mapping[str, Any]) -> dict[str, Any]:
        document = self._validate_document(candidate_document)
        # A monetary amount alone is never a safe review identity. In particular,
        # several unrelated clauses can contain INR 5,000 or INR 1,00,000. Keep
        # candidates together only when they point to the same bounded evidence
        # window in the same source document.
        groups: dict[tuple[str, str, int | float, str, str, str], list[dict[str, Any]]] = defaultdict(list)
        ignored_count = 0
        for candidate in document["candidates"]:
            if not isinstance(candidate, Mapping):
                ignored_count += 1
                continue
            value = candidate.get("normalized_value")
            if (
                candidate.get("candidate_type") != "currency_amount"
                or not isinstance(value, Mapping)
                or value.get("kind") != "currency"
                or value.get("unit") != "INR"
                or not isinstance(value.get("value"), (int, float))
            ):
                ignored_count += 1
                continue
            scope = self._infer_scope(candidate)
            evidence_identity = self._bounded_evidence_identity(candidate)
            groups[(
                "currency_amount",
                "INR",
                value["value"],
                scope["benefit_scope_key"],
                scope["band_scope_key"],
                evidence_identity,
            )].append(dict(candidate))

        reviewed_groups = [self._build_group(key, occurrences) for key, occurrences in groups.items()]
        reviewed_groups.sort(key=lambda group: (
            group["normalized_value"]["value"],
            group["group_id"],
        ))
        return {
            "schema_version": "1.0",
            "review_type": self.REVIEW_TYPE,
            "review_layer": "currency_candidate_review",
            "review_layer_version": self.VERSION,
            "status": "review_records_generated" if reviewed_groups else "no_supported_currency_candidates",
            "source": dict(document["source"]),
            "input": {
                "contract_type": document["contract_type"],
                "primitive": document["primitive"],
                "primitive_version": document["primitive_version"],
                "input_candidate_count": document["candidate_count"],
                "ignored_non_currency_candidate_count": ignored_count,
            },
            "review_group_count": len(reviewed_groups),
            "review_groups": reviewed_groups,
            "limitations": [
                "Review records organize evidence candidates only; they are not canonical facts, publication decisions, or applicability decisions.",
                "Role and scope cues are deterministic hints from extraction output and nearby pre-amount text; they are not authoritative legal interpretation.",
                "Table/column binding, option selection, policy schedule binding, and currentness remain outside this layer.",
                "Same-value candidates are split when deterministic benefit or sum-insured-band scope hints differ; unresolved scope never establishes applicability.",
                "A reviewer must resolve every group before any governed fact consideration.",
            ],
        }

    @classmethod
    def _build_group(
        cls,
        key: tuple[str, str, int | float, str, str, str],
        occurrences: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candidate_type, unit, amount, benefit_scope_key, band_scope_key, evidence_identity = key
        occurrences.sort(key=lambda item: (
            item.get("evidence", {}).get("page_number", 0),
            item.get("evidence", {}).get("character_start", 0),
            item.get("candidate_id", ""),
        ))
        role_hints = cls._unique(
            item.get("attributes", {}).get("monetary_role_hint", "monetary_amount_unresolved")
            for item in occurrences
        )
        condition_hints = cls._unique(
            hint
            for item in occurrences
            for hint in item.get("attributes", {}).get("condition_hints", [])
            if isinstance(hint, str)
        )
        pages = cls._unique(
            item.get("evidence", {}).get("page_number")
            for item in occurrences
            if isinstance(item.get("evidence", {}).get("page_number"), int)
        )
        inferred_scope = cls._group_scope(occurrences, benefit_scope_key, band_scope_key)
        flags = cls._review_flags(occurrences, role_hints, condition_hints, inferred_scope)
        group_id = cls._group_id(
            candidate_type,
            unit,
            amount,
            inferred_scope,
            evidence_identity,
            occurrences,
        )
        return {
            "group_id": group_id,
            "candidate_type": candidate_type,
            "normalized_value": {"kind": "currency", "value": amount, "unit": unit},
            "occurrence_count": len(occurrences),
            "supporting_pages": pages,
            "observed_role_hints": role_hints,
            "condition_hints": condition_hints or ["scope_unresolved"],
            "inferred_scope": inferred_scope,
            "review_flags": flags,
            "recommended_review_status": "human_resolution_required",
            "review_questions": cls._review_questions(flags, role_hints, condition_hints),
            "bounded_evidence_identity": evidence_identity,
            "supporting_candidates": occurrences,
            "bounded_evidence": cls._bounded_evidence(occurrences),
            "non_fact_guardrail": "review_record_only_no_canonical_fact",
        }

    @classmethod
    def _review_flags(
        cls,
        occurrences: list[dict[str, Any]],
        role_hints: list[str],
        condition_hints: list[str],
        inferred_scope: Mapping[str, Any],
    ) -> list[str]:
        flags: list[str] = ["role_selection_required"]
        if len(occurrences) > 1:
            flags.append("repeated_same_amount")
        if len({item.get("evidence", {}).get("page_number") for item in occurrences}) > 1:
            flags.append("repeated_across_pages")
        if len(role_hints) > 1:
            flags.append("conflicting_role_hints")
        if "monetary_amount_unresolved" in role_hints:
            flags.append("unresolved_role_hint")
        if "sum_insured_band_reference" in condition_hints:
            flags.append("schedule_or_band_binding_unverified")
        if inferred_scope.get("benefit_scope_key") == "scope_unresolved":
            flags.append("benefit_scope_unresolved")
        else:
            flags.append("benefit_scope_inferred_for_grouping")
        if inferred_scope.get("band_scope_key") == "band_unresolved" and "sum_insured_band_reference" in condition_hints:
            flags.append("sum_insured_band_scope_unresolved")
        if any("table" in str(item.get("evidence", {}).get("text", "")).lower() for item in occurrences):
            flags.append("table_layout_binding_possible")
        if cls._possible_benefit_limit_misclassification(occurrences, role_hints):
            flags.append("possible_benefit_limit_despite_role_hint")
        return flags

    @classmethod
    def _possible_benefit_limit_misclassification(cls, occurrences: list[dict[str, Any]], role_hints: list[str]) -> bool:
        if not set(role_hints).intersection({"premium", "deductible"}):
            return False
        evidence_text = " ".join(str(item.get("evidence", {}).get("text", "")) for item in occurrences).lower()
        return any(term in evidence_text for term in cls._BENEFIT_LIMIT_TERMS)

    @staticmethod
    def _review_questions(flags: list[str], role_hints: list[str], condition_hints: list[str]) -> list[str]:
        questions = ["What monetary role does this amount represent for the specific benefit or clause?"]
        if "conflicting_role_hints" in flags:
            questions.append("Do the occurrences represent different clauses rather than one reusable monetary value?")
        if "possible_benefit_limit_despite_role_hint" in flags:
            questions.append("Does nearby benefit/limit wording contradict the extracted role hint?")
        if "schedule_or_band_binding_unverified" in flags:
            questions.append("Which sum-insured band, plan variant, or column does this amount bind to?")
        if "repeated_same_amount" in flags:
            questions.append("Are repeated occurrences duplicates, or separately applicable benefits/conditions?")
        if "monetary_amount_unresolved" in role_hints:
            questions.append("Is the amount a limit, premium, deductible, sum insured, or another monetary condition?")
        if "scope_unresolved" in condition_hints:
            questions.append("What benefit, insured person, claim type, or policy option defines the amount's scope?")
        return questions

    @classmethod
    def _infer_scope(cls, candidate: Mapping[str, Any]) -> dict[str, str]:
        """Infer a narrow, review-only scope hint for a single currency occurrence.

        The previous approach selected the nearest label in a broad evidence
        window. In multi-amount clauses, that can attach an earlier amount's
        qualifier to a later amount. This version first looks for an immediate
        post-amount qualifier (for example, ``INR 1,200 for specialists``), then
        falls back to bounded nearest-label evidence. It never turns a hint into
        an applicability decision.
        """
        evidence = candidate.get("evidence", {})
        text = str(evidence.get("text", ""))
        lower = text.lower()
        value = candidate.get("normalized_value", {}).get("value")
        amount_spans = cls._currency_amount_spans(lower, value)
        if amount_spans:
            # Candidate evidence windows are bounded around the matched amount.
            # When an amount repeats, choosing the earliest matching span is
            # safer than borrowing a later benefit label; ambiguity stays review-only.
            amount_start, amount_end = amount_spans[0]
        else:
            raw_text = str(candidate.get("normalized_value", {}).get("raw_text", ""))
            amount_start = lower.find(raw_text.lower()) if raw_text else -1
            amount_end = amount_start + len(raw_text) if amount_start >= 0 else -1
        if amount_start < 0:
            amount_start = len(lower)
            amount_end = amount_start

        prefix = lower[max(0, amount_start - 650):amount_start]
        immediate_suffix = lower[amount_end:min(len(lower), amount_end + 120)]
        suffix = lower[amount_start:min(len(lower), amount_end + 140)]

        benefit_scope_key = cls._immediate_post_amount_scope(immediate_suffix)
        if benefit_scope_key == "scope_unresolved":
            label_hits: list[tuple[int, str]] = []
            for key, label in cls._SCOPE_LABELS:
                pos = prefix.rfind(label)
                if pos >= 0:
                    label_hits.append((len(prefix) - (pos + len(label)), key))
            for key, label in cls._SCOPE_LABELS:
                pos = suffix.find(label)
                if pos >= 0:
                    label_hits.append((pos, key))
            benefit_scope_key = min(label_hits)[1] if label_hits else "scope_unresolved"

        band_matches = list(re.finditer(
            r"for\s+si\s+(?:up\s+to|above|more\s+than|less\s+than)?\s*[^–—\-\n.;]{1,55}",
            prefix,
            re.I,
        ))
        if band_matches:
            band_scope_key = re.sub(r"\s+", "_", band_matches[-1].group(0).strip().lower())
        else:
            band_scope_key = "band_unresolved"
        return {"benefit_scope_key": benefit_scope_key, "band_scope_key": band_scope_key}

    @staticmethod
    def _currency_amount_spans(text: str, value: Any) -> list[tuple[int, int]]:
        """Locate explicit INR amounts equal to the candidate numeric value."""
        if not isinstance(value, (int, float)):
            return []
        target = int(value) if float(value).is_integer() else value
        spans: list[tuple[int, int]] = []
        pattern = re.compile(r"(?:inr|rs\.?|₹)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:lac|lakh|crore)?", re.I)
        for match in pattern.finditer(text):
            numeric = match.group(1).replace(",", "")
            try:
                parsed = float(numeric) if "." in numeric else int(numeric)
            except ValueError:
                continue
            if parsed == target:
                spans.append((match.start(), match.end()))
        return spans

    @classmethod
    def _immediate_post_amount_scope(cls, suffix: str) -> str:
        """Resolve explicit ``amount for <benefit>`` qualifiers before fallback."""
        bounded = suffix[:120]
        qualifier_patterns = (
            ("specialist_consultation", r"^\s*(?:for\s+)?specialists?\b"),
            ("general_physician_consultation", r"^\s*(?:for\s+)?general\s+physician\b"),
            ("family_visit", r"^\s*(?:for\s+)?family\s+visit\b"),
            ("airlift", r"^\s*(?:for\s+)?air\s*lift\b"),
        )
        for key, pattern in qualifier_patterns:
            if re.search(pattern, bounded, re.I):
                return key
        return "scope_unresolved"

    @classmethod
    def _group_scope(
        cls,
        occurrences: list[dict[str, Any]],
        benefit_scope_key: str,
        band_scope_key: str,
    ) -> dict[str, Any]:
        return {
            "benefit_scope_key": benefit_scope_key,
            "band_scope_key": band_scope_key,
            "scope_inference_method": "deterministic_pre_amount_text_hint",
            "scope_inference_requires_review": True,
        }

    @staticmethod
    def _group_id(
        candidate_type: str,
        unit: str,
        amount: int | float,
        inferred_scope: Mapping[str, Any],
        evidence_identity: str,
        occurrences: list[dict[str, Any]],
    ) -> str:
        source_sha = occurrences[0]["source"]["sha256"]
        payload = json.dumps({
            "type": candidate_type,
            "unit": unit,
            "amount": amount,
            "scope": dict(inferred_scope),
            "source": source_sha,
            "bounded_evidence_identity": evidence_identity,
        }, sort_keys=True)
        return "crgrp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def _bounded_evidence_identity(cls, candidate: Mapping[str, Any]) -> str:
        """Create a deterministic identity for the exact evidence window under review.

        Page and character offsets are part of the identity. Matching currency
        amounts in separate clauses therefore remain independently reviewable.
        """
        evidence = candidate.get("evidence", {})
        source = candidate.get("source", {})
        payload = {
            "source_sha256": source.get("sha256"),
            "page_number": evidence.get("page_number"),
            "character_start": evidence.get("character_start"),
            "character_end": evidence.get("character_end"),
            "normalized_character_start": evidence.get("normalized_character_start"),
            "normalized_character_end": evidence.get("normalized_character_end"),
            "evidence_type": evidence.get("evidence_type"),
            "text": re.sub(r"\s+", " ", str(evidence.get("text", "")).strip()),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:20]

    @staticmethod
    def _bounded_evidence(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Retain the reviewer-visible evidence needed to verify each group."""
        items: list[dict[str, Any]] = []
        for candidate in occurrences:
            attributes = candidate.get("attributes", {})
            evidence = candidate.get("evidence", {})
            normalized_value = candidate.get("normalized_value", {})
            items.append({
                "candidate_id": candidate.get("candidate_id"),
                "normalized_value": {
                    "kind": normalized_value.get("kind"),
                    "value": normalized_value.get("value"),
                    "unit": normalized_value.get("unit"),
                    "raw_text": normalized_value.get("raw_text"),
                },
                "role_hint": attributes.get("monetary_role_hint"),
                "condition_hints": list(attributes.get("condition_hints", [])),
                "evidence": {
                    "text": evidence.get("text"),
                    "page_number": evidence.get("page_number"),
                    "character_start": evidence.get("character_start"),
                    "character_end": evidence.get("character_end"),
                    "normalized_character_start": evidence.get("normalized_character_start"),
                    "normalized_character_end": evidence.get("normalized_character_end"),
                    "evidence_type": evidence.get("evidence_type"),
                },
            })
        return items

    @staticmethod
    def _unique(values: Any) -> list[Any]:
        seen: set[Any] = set()
        result: list[Any] = []
        for value in values:
            if value is None or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @staticmethod
    def _validate_document(document: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(document, Mapping):
            raise CurrencyCandidateReviewError("candidate_document must be an object")
        if document.get("contract_type") != ExtractionCandidateContract.ENVELOPE_TYPE:
            raise CurrencyCandidateReviewError("candidate_document must use the shared extraction candidate contract")
        if not isinstance(document.get("candidates"), list):
            raise CurrencyCandidateReviewError("candidate_document.candidates must be a list")
        if not isinstance(document.get("candidate_count"), int):
            raise CurrencyCandidateReviewError("candidate_document.candidate_count must be an integer")
        if document["candidate_count"] != len(document["candidates"]):
            raise CurrencyCandidateReviewError("candidate_count does not match candidates length")
        try:
            ExtractionCandidateContract.validate_source(document.get("source"))
        except Exception as exc:
            raise CurrencyCandidateReviewError(str(exc)) from exc
        return document
