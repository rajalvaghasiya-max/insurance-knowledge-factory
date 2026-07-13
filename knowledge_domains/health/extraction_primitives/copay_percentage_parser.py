"""Deterministic co-pay percentage evidence-candidate primitive.

Detects explicit percentage co-pay clauses in existing parsed PDF text. It emits
review-required evidence candidates only; it never determines product-wide
applicability, selects an option, or creates canonical facts.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from .extraction_candidate_contract import ExtractionCandidateContract


class CopayPercentageParserError(ValueError):
    """Raised when an input parse artifact lacks required provenance."""


class CopayPercentageParser:
    VERSION = "1.1"
    PRIMITIVE_NAME = "copay_percentage_parser"

    _PERCENT_RE = re.compile(r"(?P<value>\d{1,3}(?:\.\d+)?)\s*%")

    _COPAY_BEFORE_PERCENT = re.compile(
        r"\b(?:co[-\s]?pay(?:ment)?|copayment)"
        r"(?:\s+(?:of|is|shall\s+be|will\s+be|at))?"
        r"\s*:?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )

    _SELECTED_COPAY_PERCENT = re.compile(
        r"\b(?:selected|chosen|opted|applicable)\s+"
        r"(?:co[-\s]?pay(?:ment)?|copayment)"
        r"\s*:?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )

    _COPAY_OPTION_PERCENT = re.compile(
        r"\b(?:co[-\s]?pay(?:ment)?|copayment)\s+option"
        r"(?:\s+(?:of|is|at))?\s*:?\s*"
        r"(?P<value>\d{1,3}(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )

    _BEAR_PERCENT_CONTEXT = re.compile(
        r"\b(?:insured|policyholder|you)\s+(?:shall|will)\s+bear\s+"
        r"(?:a\s+)?(?P<value>\d{1,3}(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )
    _COPAY_CONTEXT = re.compile(
        r"\b(?:co[-\s]?pay(?:ment)?|copayment)\b", re.IGNORECASE
    )
    _WAIVED_RE = re.compile(
        r"\b(?:no|nil|zero)\s+(?:co[-\s]?pay(?:ment)?|copayment)"
        r"|(?:co[-\s]?pay(?:ment)?|copayment)\s+(?:is\s+)?waived\b",
        re.IGNORECASE,
    )
    _VOLUNTARY_RE = re.compile(
        r"\bvoluntary\s+co[-\s]?pay(?:ment)?\b"
        r"|\bco[-\s]?pay(?:ment)?\s+option\b",
        re.IGNORECASE,
    )
    _MANDATORY_RE = re.compile(
        r"\bmandatory\s+co[-\s]?pay(?:ment)?\b", re.IGNORECASE
    )
    _OPTION_RE = re.compile(
        r"\b(?:option|opted|discount|proportion\s+to)\b", re.IGNORECASE
    )
    _SCOPE_PATTERNS = (
        (
            "reimbursement_non_preapproved",
            re.compile(r"\b(?:reimbursement|not\s+pre-approved)\b", re.IGNORECASE),
        ),
        (
            "travel_or_international_benefit",
            re.compile(
                r"\b(?:outside\s+india|travel|single\s+trip|international)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "voluntary_option",
            re.compile(
                r"\bvoluntary\s+co[-\s]?pay(?:ment)?\b"
                r"|\bco[-\s]?pay(?:ment)?\s+option\b",
                re.IGNORECASE,
            ),
        ),
    )

    def extract_from_parsed_document(
        self, parsed_document: Mapping[str, Any]
    ) -> dict[str, Any]:
        document = self._validate_document(parsed_document)
        candidates: list[dict[str, Any]] = []
        pages_examined = 0
        for page in document["pages"]:
            if not isinstance(page, Mapping):
                continue
            page_number = page.get("page_number")
            text = page.get("text")
            if (
                not isinstance(page_number, int)
                or page_number <= 0
                or not isinstance(text, str)
                or not text.strip()
            ):
                continue
            pages_examined += 1
            candidates.extend(self._extract_page(document, page_number, text))

        candidates.sort(
            key=lambda item: (
                item["evidence"]["page_number"],
                item["evidence"]["character_start"],
                item["candidate_id"],
            )
        )
        result = ExtractionCandidateContract.build_document(
            primitive=self.PRIMITIVE_NAME,
            primitive_version=self.VERSION,
            source=self._source_provenance(document),
            candidates=candidates,
            status="candidates_extracted" if candidates else "no_supported_evidence",
            limitations=[
                "Candidates are evidence leads only; they are not canonical facts or publication decisions.",
                "A percentage candidate does not prove product-wide applicability, selection, waiver, or claim-order semantics.",
                "Table reconstruction, option selection, deductible interaction, and currentness are outside this primitive.",
            ],
        )
        result["pages_examined"] = pages_examined
        return result

    def extract_from_pages(
        self,
        *,
        pages: Iterable[Mapping[str, Any]],
        source: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.extract_from_parsed_document(
            {**dict(source), "pages": list(pages)}
        )

    def _extract_page(
        self,
        document: Mapping[str, Any],
        page_number: int,
        original_text: str,
    ) -> list[dict[str, Any]]:
        normalized, index_map = self._normalize_with_index_map(original_text)
        if not normalized:
            return []

        matches: list[tuple[re.Match[str], str]] = []
        matches.extend(
            (match, "explicit_copay_percentage")
            for match in self._COPAY_BEFORE_PERCENT.finditer(normalized)
        )
        matches.extend(
            (match, "selected_copay_percentage")
            for match in self._SELECTED_COPAY_PERCENT.finditer(normalized)
        )
        matches.extend(
            (match, "copay_option_percentage")
            for match in self._COPAY_OPTION_PERCENT.finditer(normalized)
        )

        for bear_match in self._BEAR_PERCENT_CONTEXT.finditer(normalized):
            tail_end = min(len(normalized), bear_match.end() + 80)
            matches.extend(
                (percentage_match, "bear_percentage_in_copay_context")
                for percentage_match in self._PERCENT_RE.finditer(
                    normalized, bear_match.start(), tail_end
                )
            )

        candidates: list[dict[str, Any]] = []
        seen: set[tuple[int, int, str]] = set()
        seen_candidate_ids: set[str] = set()
        for match, match_kind in sorted(
            matches,
            key=lambda item: (item[0].start(), item[0].end(), item[1]),
        ):
            start, end = match.start(), match.end()
            value_key = str(match.group("value"))
            key = (start, end, value_key)
            if key in seen:
                continue

            window_start = max(0, start - 180)
            window_end = min(len(normalized), end + 260)
            evidence_text = normalized[window_start:window_end].strip()
            if (
                match_kind == "bear_percentage_in_copay_context"
                and not self._COPAY_CONTEXT.search(evidence_text)
            ):
                continue
            seen.add(key)

            value_float = float(match.group("value"))
            value: int | float = (
                int(value_float) if value_float.is_integer() else value_float
            )
            source = self._source_provenance(document)
            normalized_value = {
                "kind": "percentage",
                "value": value,
                "unit": "percent",
                "raw_text": f"{match.group('value')}%",
            }
            candidate_id = ExtractionCandidateContract.deterministic_candidate_id(
                primitive=self.PRIMITIVE_NAME,
                source_sha256=source["sha256"],
                page_number=page_number,
                normalized_character_start=window_start,
                normalized_character_end=window_end,
                candidate_type="copay_percentage",
                normalized_value=normalized_value,
            )
            if candidate_id in seen_candidate_ids:
                continue
            seen_candidate_ids.add(candidate_id)
            candidates.append(
                ExtractionCandidateContract.build_candidate(
                    candidate_id=candidate_id,
                    candidate_type="copay_percentage",
                    normalized_value=normalized_value,
                    attributes={
                        "copay_status": "explicit_percentage",
                        "copay_mode": self._mode(evidence_text),
                        "scope_hints": self._scope_hints(evidence_text),
                        "waiver_signal": bool(
                            self._WAIVED_RE.search(evidence_text)
                        ),
                        "match_kind": match_kind,
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
                        "score": self._confidence(evidence_text),
                        "method": "deterministic_regex_context",
                        "requires_review": True,
                        "reason": (
                            "Explicit percentage found in bounded co-pay context; "
                            "scope, option selection, claim-order and layout fidelity "
                            "remain unverified."
                        ),
                    },
                )
            )
        return candidates

    @classmethod
    def _mode(cls, text: str) -> str:
        if cls._VOLUNTARY_RE.search(text):
            return "voluntary_or_option"
        if cls._MANDATORY_RE.search(text):
            return "mandatory"
        if cls._OPTION_RE.search(text):
            return "option_or_discount_related"
        return "unspecified"

    @classmethod
    def _scope_hints(cls, text: str) -> list[str]:
        return [
            name
            for name, pattern in cls._SCOPE_PATTERNS
            if pattern.search(text)
        ] or ["scope_unresolved"]

    @staticmethod
    def _confidence(text: str) -> float:
        return (
            0.83
            if re.search(
                r"\b(?:mandatory|voluntary|reimbursement|claim|selected)\b",
                text,
                re.IGNORECASE,
            )
            else 0.78
        )

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
            "entity_id",
            "insurer_id",
            "document_type",
            "source_document_id",
            "sha256",
            "source_url",
            "source_page_url",
            "relative_archive_path",
            "provenance_status",
        )
        return {key: document.get(key) for key in keys}

    @staticmethod
    def _validate_document(
        document: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if not isinstance(document, Mapping):
            raise CopayPercentageParserError(
                "parsed_document must be an object"
            )
        if not isinstance(document.get("pages"), list):
            raise CopayPercentageParserError(
                "parsed_document.pages must be a list"
            )
        try:
            ExtractionCandidateContract.validate_source(document)
        except Exception as exc:
            raise CopayPercentageParserError(str(exc)) from exc
        return document
