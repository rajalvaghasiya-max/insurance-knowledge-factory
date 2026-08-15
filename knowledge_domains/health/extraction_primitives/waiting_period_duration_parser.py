from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .extraction_candidate_contract import ExtractionCandidateContract


@dataclass(frozen=True)
class _DurationMatch:
    value: int
    unit: str
    raw_value: str
    start: int
    end: int


class WaitingPeriodDurationParser:
    """Extract waiting-period *evidence candidates* from parsed PDF text.

    This primitive is deliberately narrower than a field extractor:
    - It requires waiting-period context and an explicit numeric duration.
    - It preserves page/source provenance and the exact evidence window.
    - It classifies only broad waiting-period categories.
    - It returns no candidate (rather than guessing) for schedule-only phrases,
      unspecified durations, or unrelated durations.

    It never creates canonical facts, changes identity/currentness, or decides
    whether a candidate is applicable to a product variant.
    """

    SCHEMA_VERSION = "1.0"
    VERSION = "1.1"
    PRIMITIVE_NAME = "waiting_period_duration_parser"

    _DURATION_RE = re.compile(
        r"(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?|months?|years?)\b",
        re.IGNORECASE,
    )
    _CATEGORY_PATTERNS = (
        (
            "pre_existing_disease",
            re.compile(
                r"(?P<label>(?:pre[- ]?existing\s+(?:diseases?|conditions?)|PED)\s+waiting\s+period(?:\s*\([^)]*\))?)"
                r"(?:\s*(?:is|of|:|=|as\s+per))?\s*(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?|months?|years?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "specified_disease_or_procedure",
            re.compile(
                r"(?P<label>specified\s+(?:disease|condition|procedure)(?:/\s*(?:disease|condition|procedure))?\s+waiting\s+period(?:\s*\([^)]*\))?)"
                r"(?:\s*(?:is|of|:|=|as\s+per))?\s*(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?|months?|years?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "initial",
            re.compile(
                r"(?P<label>initial\s+(?:(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?|months?|years?)\s+)?waiting\s+period(?:\s*\([^)]*\))?)"
                r"(?:\s*(?:is|of|:|=|applies))?\s*(?:(?P<num_after>\d{1,3})\s*[- ]?\s*(?P<unit_after>days?|months?|years?)\b)?",
                re.IGNORECASE,
            ),
        ),
        (
            "initial",
            re.compile(
                r"(?P<label>(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?)\s+waiting\s+period\s*\([^)]*code\s*-?\s*excl\s*0?3[^)]*\))",
                re.IGNORECASE,
            ),
        ),
        (
            "maternity",
            re.compile(
                r"(?P<label>maternity(?:\s+expenses?)?\s+waiting\s+period(?:\s*\([^)]*\))?)"
                r"(?:\s*(?:is|of|:|=|as\s+per))?\s*(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?|months?|years?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "baby_care",
            re.compile(
                r"(?P<label>baby\s+care\s+waiting\s+period(?:\s*\([^)]*\))?)"
                r"(?:\s*(?:is|of|:|=|as\s+per))?\s*(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?|months?|years?)\b",
                re.IGNORECASE,
            ),
        ),
    )
    _CLAUSE_CATEGORY_PATTERNS = (
        (
            "specified_disease_or_procedure",
            re.compile(
                r"(?P<label>speci(?:fied|ﬁed)\s+disease\s*/\s*procedure\s+waiting\s+period(?:\s*:\s*)?(?:\([^)]*\))?)"
                r"(?P<body>.{0,500}?\bshall\s+be\s+excluded\s+until\s+the\s+expiry\s+of\s+)"
                r"(?P<num>\d{1,3})\s*[- ]?\s*(?P<unit>days?|months?|years?)\b",
                re.IGNORECASE,
            ),
        ),
    )
    _SCHEDULE_ONLY_RE = re.compile(
        r"\b(?:as\s+(?:specified|mentioned|opted)\s+(?:in|on)\s+(?:the\s+)?policy\s+schedule|"
        r"policy\s+schedule\s+(?:would|will)\s+(?:specify|apply))\b",
        re.IGNORECASE,
    )

    def extract_from_parsed_document(self, parsed_document: Mapping[str, Any]) -> dict[str, Any]:
        """Return deterministic waiting-period evidence candidates for one parsed PDF.

        ``parsed_document`` must be a registry-backed native-text parse artifact
        with a ``pages`` list containing ``page_number`` and ``text``.
        """
        document = self._validate_document(parsed_document)
        candidates: list[dict[str, Any]] = []
        pages_examined = 0

        for page in document["pages"]:
            if not isinstance(page, Mapping):
                continue
            page_number = page.get("page_number")
            text = page.get("text")
            if not isinstance(page_number, int) or not isinstance(text, str) or not text.strip():
                continue
            pages_examined += 1
            candidates.extend(self._extract_page(document, page_number, text))

        candidates.sort(key=lambda item: (item["evidence"]["page_number"], item["evidence"]["character_start"], item["candidate_id"]))
        result = ExtractionCandidateContract.build_document(
            primitive=self.PRIMITIVE_NAME,
            primitive_version=self.VERSION,
            status="candidates_extracted" if candidates else "no_supported_evidence",
            source=self._source_provenance(document),
            candidates=candidates,
            limitations=[
                "Candidates are evidence leads only; they are not canonical facts or publication decisions.",
                "Schedule-only or unspecified waiting periods are intentionally not converted into numeric candidates.",
                "Table reconstruction, reading order, applicability, and currentness are outside this primitive.",
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
        """Convenience entry point for tests and parser integrations.

        The caller supplies the same source fields normally retained by the
        registry-backed parse artifact.
        """
        document = {**dict(source), "pages": list(pages)}
        return self.extract_from_parsed_document(document)

    def _extract_page(self, document: Mapping[str, Any], page_number: int, text: str) -> list[dict[str, Any]]:
        normalized, index_map = self._normalize_with_index_map(text)
        if not normalized:
            return []

        candidates: list[dict[str, Any]] = []
        seen: set[tuple[int, int, str]] = set()
        for category, pattern in (*self._CATEGORY_PATTERNS, *self._CLAUSE_CATEGORY_PATTERNS):
            for match in pattern.finditer(normalized):
                number_text = match.groupdict().get("num") or match.groupdict().get("num_after")
                unit_text = match.groupdict().get("unit") or match.groupdict().get("unit_after")
                if not number_text or not unit_text:
                    continue
                duration = _DurationMatch(
                    value=int(number_text),
                    unit=self._canonical_unit(unit_text),
                    raw_value=f"{int(number_text)} {self._canonical_unit(unit_text)}",
                    start=match.start(),
                    end=match.end(),
                )
                key = (match.start(), match.end(), category)
                if key in seen:
                    continue
                seen.add(key)
                evidence_start = max(0, match.start() - 120)
                evidence_end = min(len(normalized), match.end() + 220)
                evidence_text = normalized[evidence_start:evidence_end].strip()
                original_start = index_map[evidence_start]
                original_end = index_map[evidence_end - 1] + 1
                candidates.append(
                    self._build_candidate(
                        document=document,
                        page_number=page_number,
                        category=category,
                        duration=duration,
                        evidence_text=evidence_text,
                        normalized_start=evidence_start,
                        normalized_end=evidence_end,
                        original_start=original_start,
                        original_end=original_end,
                    )
                )
        return candidates

    def _build_candidate(
        self,
        *,
        document: Mapping[str, Any],
        page_number: int,
        category: str,
        duration: _DurationMatch,
        evidence_text: str,
        normalized_start: int,
        normalized_end: int,
        original_start: int,
        original_end: int,
    ) -> dict[str, Any]:
        normalized_value = {
            "kind": "duration",
            "value": duration.value,
            "unit": duration.unit,
            "raw_text": duration.raw_value,
        }
        evidence = {
            "text": evidence_text,
            "page_number": page_number,
            "character_start": original_start,
            "character_end": original_end,
            "normalized_character_start": normalized_start,
            "normalized_character_end": normalized_end,
            "evidence_type": "native_text_clause_window",
        }
        source = self._source_provenance(document)
        candidate_id = ExtractionCandidateContract.deterministic_candidate_id(
            primitive=self.PRIMITIVE_NAME,
            source_sha256=source["sha256"],
            page_number=page_number,
            normalized_character_start=normalized_start,
            normalized_character_end=normalized_end,
            candidate_type="waiting_period_duration",
            normalized_value=normalized_value,
        )
        return ExtractionCandidateContract.build_candidate(
            candidate_id=candidate_id,
            candidate_type="waiting_period_duration",
            normalized_value=normalized_value,
            attributes={
                "waiting_period_category": category,
                "normalized_months": self._normalized_months(duration.value, duration.unit),
            },
            evidence=evidence,
            source=source,
            confidence={
                "score": self._confidence(category, evidence_text),
                "method": "deterministic_regex_context",
                "requires_review": True,
                "reason": "Explicit duration found in bounded waiting-period context; applicability and layout/table fidelity remain unverified.",
            },
        )

    @staticmethod
    def _classify_category(text: str) -> str:
        normalized = text.lower()
        if re.search(r"\b(?:pre[- ]?existing|\bped\b)\b", normalized):
            return "pre_existing_disease"
        if re.search(r"\b(?:specified\s+disease|specified\s+condition|specified\s+procedure|time[- ]?bound)\b", normalized):
            return "specified_disease_or_procedure"
        if re.search(r"\b(?:maternity|pregnancy)\b", normalized):
            return "maternity"
        if re.search(r"\b(?:baby\s+care|new[- ]?born)\b", normalized):
            return "baby_care"
        if re.search(r"\b(?:initial|first\s+policy|code[- ]?excl03)\b", normalized):
            return "initial"
        return "unspecified_waiting_period"

    @staticmethod
    def _confidence(category: str, evidence_text: str) -> float:
        score = 0.68
        if category != "unspecified_waiting_period":
            score += 0.10
        if re.search(r"\b(?:excluded|not\s+applicable|except|coverage)\b", evidence_text, re.IGNORECASE):
            score += 0.05
        return min(score, 0.83)

    @staticmethod
    def _canonical_unit(unit: str) -> str:
        unit = unit.lower()
        if unit.startswith("day"):
            return "days"
        if unit.startswith("month"):
            return "months"
        return "years"

    @staticmethod
    def _normalized_months(value: int, unit: str) -> int | None:
        if unit == "months":
            return value
        if unit == "years":
            return value * 12
        return None

    @staticmethod
    def _normalize_with_index_map(text: str) -> tuple[str, list[int]]:
        chars: list[str] = []
        positions: list[int] = []
        prior_was_space = False
        for index, char in enumerate(text):
            if char.isspace():
                if prior_was_space:
                    continue
                chars.append(" ")
                positions.append(index)
                prior_was_space = True
            else:
                chars.append(char)
                positions.append(index)
                prior_was_space = False
        normalized = "".join(chars).strip()
        if not normalized:
            return "", []
        left_trim = len("".join(chars)) - len("".join(chars).lstrip())
        right_trim = len("".join(chars)) - len("".join(chars).rstrip())
        if right_trim:
            positions = positions[left_trim:-right_trim]
        else:
            positions = positions[left_trim:]
        return normalized, positions

    @staticmethod
    def _source_provenance(document: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "entity_id": document.get("entity_id"),
            "insurer_id": document.get("insurer_id"),
            "document_type": document.get("document_type"),
            "source_document_id": document.get("source_document_id"),
            "sha256": document.get("sha256"),
            "source_url": document.get("source_url"),
            "source_page_url": document.get("source_page_url"),
            "relative_archive_path": document.get("relative_archive_path"),
            "provenance_status": document.get("provenance_status"),
        }

    @staticmethod
    def _validate_document(parsed_document: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(parsed_document, Mapping):
            raise ValueError("parsed_document must be a mapping")
        pages = parsed_document.get("pages")
        if not isinstance(pages, list):
            raise ValueError("parsed_document.pages must be a list")
        sha256 = parsed_document.get("sha256")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError("parsed_document.sha256 must be a 64-character lowercase SHA-256")
        return parsed_document