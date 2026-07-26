"""Shared, provenance-preserving UIN candidate extraction.

A detected UIN is a discovery candidate only. This module validates format and
preserves local source evidence; it deliberately does not assign product
ownership or create a verified Product Identity link.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UinCandidate:
    """A format-valid UIN occurrence with local evidence and source context."""

    uin: str
    extraction_method: str
    raw_text: str
    evidence_text: str
    match_start: int
    match_end: int
    source: dict[str, Any]
    candidate_status: str = "format_valid_candidate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "uin": self.uin,
            "candidate_status": self.candidate_status,
            "extraction_method": self.extraction_method,
            "raw_text": self.raw_text,
            "evidence_text": self.evidence_text,
            "match_start": self.match_start,
            "match_end": self.match_end,
            "source": self.source,
        }


class UinCandidateExtractor:
    """Extracts labelled, format-valid UIN candidates from source text.

    Detection is intentionally label-led. A UIN-shaped string without a nearby
    UIN label is not promoted into the candidate stream, reducing accidental
    capture of unrelated reference codes.
    """

    VERSION = "1.0"
    _PATTERN = re.compile(
        r"(?P<label>"
        r"product\s+uin|"
        r"uin\s*(?:no\.?|number)?|"
        r"unique\s+identification\s+(?:no\.?|number)"
        r")\s*[:\-]?\s*(?P<uin>[a-z0-9]{8,30})\b",
        flags=re.IGNORECASE,
    )

    def extract(
        self,
        text: str,
        *,
        source: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return labelled, format-valid UIN candidates in source order."""
        if not text:
            return []

        source_context = dict(source or {})
        candidates: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()

        for match in self._PATTERN.finditer(text):
            uin = match.group("uin").upper()
            if not self.is_format_valid(uin):
                continue

            marker = (uin, match.start())
            if marker in seen:
                continue
            seen.add(marker)

            candidate = UinCandidate(
                uin=uin,
                extraction_method=self._method_for_label(match.group("label")),
                raw_text=match.group(0).strip(),
                evidence_text=self._evidence_window(text, match.start(), match.end()),
                match_start=match.start(),
                match_end=match.end(),
                source=source_context,
            )
            candidates.append(candidate.to_dict())

        return candidates

    @staticmethod
    def is_format_valid(value: str | None) -> bool:
        """Validate generic UIN structure without asserting product ownership."""
        if not value:
            return False

        candidate = value.strip().upper()
        if "XXXXX" in candidate:
            return False
        if not re.fullmatch(r"[A-Z0-9]{8,30}", candidate):
            return False
        if not re.search(r"[A-Z]", candidate):
            return False
        if not re.search(r"\d", candidate):
            return False
        return bool(re.search(r"V\d{2,}", candidate))

    @staticmethod
    def _method_for_label(label: str) -> str:
        normalized = re.sub(r"\s+", " ", label.lower()).strip()
        if normalized.startswith("product uin"):
            return "product_uin_label"
        if normalized.startswith("unique identification"):
            return "unique_identification_label"
        return "uin_label"

    @staticmethod
    def _evidence_window(text: str, start: int, end: int, radius: int = 140) -> str:
        left = max(0, start - radius)
        right = min(len(text), end + radius)
        return re.sub(r"\s+", " ", text[left:right]).strip()
