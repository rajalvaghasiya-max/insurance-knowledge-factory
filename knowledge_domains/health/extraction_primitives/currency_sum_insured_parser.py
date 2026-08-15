"""Deterministic monetary evidence-candidate primitive for Health PDFs.

Finds explicit INR/Rs/₹ amounts in bounded monetary context. Emits evidence
candidates only; it never selects a base sum insured, a sub-limit, a deductible,
or a premium as a product fact.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from .extraction_candidate_contract import ExtractionCandidateContract


class CurrencySumInsuredParserError(ValueError):
    """Raised when a parsed PDF artifact lacks shared source provenance."""


class CurrencySumInsuredParser:
    VERSION = "1.0"
    PRIMITIVE_NAME = "currency_sum_insured_parser"

    # Explicit currency only. Bare ``5 Lac``/``10 lakh`` strings are deliberately
    # excluded: without a currency marker they may be a sum-insured band, a page
    # label, a count, or malformed table text.
    _AMOUNT_RE = re.compile(
        r"(?P<currency>₹|\bINR(?=\s|\d)|\bRs\.?(?=\s|\d)|\bRupees\b)\s*(?P<amount>\d[\d,]*(?:\.\d+)?)"
        r"(?:\s*(?P<scale>lac|lacs|lakh|lakhs|crore|crores))?",
        re.IGNORECASE,
    )
    _ROLE_PATTERNS = (
        ("deductible", re.compile(r"\bdeductible\b", re.IGNORECASE)),
        ("premium", re.compile(r"\bpremium\b", re.IGNORECASE)),
        ("sum_insured", re.compile(r"\b(?:sum\s+insured|sum-insured)\b", re.IGNORECASE)),
        ("sub_limit_or_limit", re.compile(r"\b(?:sub[-\s]?limit|limit|up\s+to|upto)\b", re.IGNORECASE)),
    )
    _IMMEDIATE_PRE_AMOUNT_LIMIT_RE = re.compile(
        r"(?:\bup\s+to\b|\bupto\b|\blimit(?:\s+for)?[^.;\n]{0,45}?\bup\s+to\b)\s*$",
        re.IGNORECASE,
    )
    _CONDITION_PATTERNS = (
        ("sum_insured_band_reference", re.compile(r"\b(?:for|above|upto|up\s+to)\s+SI\b|\bSI\s+\d", re.IGNORECASE)),
        ("claim_or_benefit_context", re.compile(r"\b(?:claim|benefit|cover|treatment|expenses?)\b", re.IGNORECASE)),
        ("policy_schedule_reference", re.compile(r"\bpolicy\s+schedule\b", re.IGNORECASE)),
    )

    def extract_from_parsed_document(self, parsed_document: Mapping[str, Any]) -> dict[str, Any]:
        document = self._validate_document(parsed_document)
        candidates: list[dict[str, Any]] = []
        pages_examined = 0
        for page in document["pages"]:
            if not isinstance(page, Mapping):
                continue
            page_number, text = page.get("page_number"), page.get("text")
            if not isinstance(page_number, int) or page_number <= 0 or not isinstance(text, str) or not text.strip():
                continue
            pages_examined += 1
            candidates.extend(self._extract_page(document, page_number, text))

        candidates.sort(key=lambda item: (
            item["evidence"]["page_number"], item["evidence"]["character_start"], item["candidate_id"]
        ))
        result = ExtractionCandidateContract.build_document(
            primitive=self.PRIMITIVE_NAME,
            primitive_version=self.VERSION,
            source=self._source_provenance(document),
            candidates=candidates,
            status="candidates_extracted" if candidates else "no_supported_evidence",
            limitations=[
                "Candidates are evidence leads only; they are not canonical facts or publication decisions.",
                "An explicit currency amount does not prove it is the base sum insured, a product-wide limit, deductible, premium, or selected option.",
                "Bare lakh/crore bands without an explicit currency marker are intentionally ignored.",
                "Table reconstruction, amount-to-column binding, applicability, and currentness are outside this primitive.",
            ],
        )
        result["pages_examined"] = pages_examined
        return result

    def extract_from_pages(self, *, pages: Iterable[Mapping[str, Any]], source: Mapping[str, Any]) -> dict[str, Any]:
        return self.extract_from_parsed_document({**dict(source), "pages": list(pages)})

    def _extract_page(self, document: Mapping[str, Any], page_number: int, original_text: str) -> list[dict[str, Any]]:
        normalized, index_map = self._normalize_with_index_map(original_text)
        if not normalized:
            return []
        source = self._source_provenance(document)
        candidates: list[dict[str, Any]] = []
        for match in self._AMOUNT_RE.finditer(normalized):
            start, end = match.start(), match.end()
            window_start = max(0, start - 180)
            window_end = min(len(normalized), end + 260)
            evidence_text = normalized[window_start:window_end].strip()
            value = self._parse_amount(match.group("amount"), match.group("scale"))
            raw_text = match.group(0).strip()
            normalized_value = {
                "kind": "currency",
                "value": value,
                "unit": "INR",
                "raw_text": raw_text,
            }
            candidate_id = ExtractionCandidateContract.deterministic_candidate_id(
                primitive=self.PRIMITIVE_NAME,
                source_sha256=source["sha256"],
                page_number=page_number,
                normalized_character_start=window_start,
                normalized_character_end=window_end,
                candidate_type="currency_amount",
                normalized_value=normalized_value,
            )
            local_context = self._local_context(normalized, start, end)
            role_context_start = max(0, start - 100)
            role_context = normalized[role_context_start:min(len(normalized), end + 100)]
            role = self._monetary_role(
                role_context,
                start - role_context_start,
                end - role_context_start,
            )
            candidates.append(
                ExtractionCandidateContract.build_candidate(
                    candidate_id=candidate_id,
                    candidate_type="currency_amount",
                    normalized_value=normalized_value,
                    attributes={
                        "monetary_role_hint": role,
                        "currency_marker": self._currency_marker(match.group("currency")),
                        "scale_token": (match.group("scale") or "").lower() or None,
                        "condition_hints": self._condition_hints(local_context),
                        "role_selection_required": True,
                        "match_kind": "explicit_currency_amount",
                    },
                    evidence={
                        "text": evidence_text,
                        "page_number": page_number,
                        "character_start": index_map[window_start],
                        "character_end": index_map[window_end - 1] + 1,
                        "normalized_character_start": window_start,
                        "normalized_character_end": window_end,
                        "evidence_type": "native_text_clause_window",
                    },
                    source=source,
                    confidence={
                        "score": self._confidence(role),
                        "method": "deterministic_regex_context",
                        "requires_review": True,
                        "reason": "Explicit currency amount found; monetary role, scope, option selection, table/column binding and applicability remain unverified.",
                    },
                )
            )
        return candidates

    @classmethod
    def _parse_amount(cls, amount_text: str, scale: str | None) -> int | float:
        base = float(amount_text.replace(",", ""))
        multiplier = 1
        if scale:
            token = scale.lower()
            if token in {"lac", "lacs", "lakh", "lakhs"}:
                multiplier = 100_000
            elif token in {"crore", "crores"}:
                multiplier = 10_000_000
        value = base * multiplier
        return int(value) if value.is_integer() else value

    @staticmethod
    def _local_context(text: str, start: int, end: int) -> str:
        """Return the nearest sentence/semicolon clause around a matched amount.

        Role hints must be local to the amount. A large evidence window can contain
        several different monetary clauses, which would otherwise mislabel every
        amount as a deductible or premium.
        """
        left = max(text.rfind(".", 0, start), text.rfind(";", 0, start), text.rfind("\n", 0, start))
        right_candidates = [index for index in (text.find(".", end), text.find(";", end), text.find("\n", end)) if index != -1]
        right = min(right_candidates) if right_candidates else len(text)
        return text[left + 1:right].strip()

    @classmethod
    def _monetary_role(cls, text: str, amount_start: int, amount_end: int) -> str:
        """Return the strongest bounded role cue for the matched amount.

        An explicit limit phrase immediately before the amount outranks a nearby
        but separate role word after the amount. This prevents compressed table
        text such as ``Family Visit ... Upto INR 25,000 Renewal premium waiver``
        from relabelling the benefit limit as a premium. The hint remains review-
        only; band/column binding and applicability are not resolved here.
        """
        prefix = text[max(0, amount_start - 60):amount_start]
        if cls._IMMEDIATE_PRE_AMOUNT_LIMIT_RE.search(prefix):
            return "sub_limit_or_limit"

        candidates: list[tuple[int, str]] = []
        for role, pattern in cls._ROLE_PATTERNS:
            for match in pattern.finditer(text):
                distance = min(abs(amount_start - match.end()), abs(match.start() - amount_end))
                candidates.append((distance, role))
        if not candidates:
            return "monetary_amount_unresolved"
        return min(candidates, key=lambda item: item[0])[1]

    @classmethod
    def _condition_hints(cls, text: str) -> list[str]:
        return [name for name, pattern in cls._CONDITION_PATTERNS if pattern.search(text)] or ["scope_unresolved"]

    @staticmethod
    def _currency_marker(marker: str) -> str:
        lowered = marker.lower().replace(".", "")
        if marker == "₹":
            return "INR_symbol"
        if lowered.startswith("rs"):
            return "Rs"
        if lowered.startswith("rupees"):
            return "Rupees"
        return "INR"

    @staticmethod
    def _confidence(role: str) -> float:
        return 0.83 if role != "monetary_amount_unresolved" else 0.78

    @staticmethod
    def _normalize_with_index_map(text: str) -> tuple[str, list[int]]:
        characters: list[str] = []
        index_map: list[int] = []
        previous_space = False
        for index, character in enumerate(text):
            if character.isspace():
                if previous_space:
                    continue
                characters.append(" ")
                index_map.append(index)
                previous_space = True
            else:
                characters.append(character)
                index_map.append(index)
                previous_space = False
        return "".join(characters), index_map

    @staticmethod
    def _source_provenance(document: Mapping[str, Any]) -> dict[str, Any]:
        keys = (
            "entity_id", "insurer_id", "document_type", "source_document_id", "sha256",
            "source_url", "source_page_url", "relative_archive_path", "provenance_status",
        )
        return {key: document.get(key) for key in keys}

    @staticmethod
    def _validate_document(document: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(document, Mapping):
            raise CurrencySumInsuredParserError("parsed_document must be an object")
        if not isinstance(document.get("pages"), list):
            raise CurrencySumInsuredParserError("parsed_document.pages must be a list")
        try:
            ExtractionCandidateContract.validate_source(document)
        except Exception as exc:
            raise CurrencySumInsuredParserError(str(exc)) from exc
        return document
