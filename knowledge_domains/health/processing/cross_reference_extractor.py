from __future__ import annotations

import re
from typing import Iterable

from .processing_models import CrossReference, SourceLocation, stable_id


class CrossReferenceExtractionEngine:
    """
    Department III — Document Processing
    Engine: Cross Reference Extraction Engine

    Responsibility:
        Detect references to sections, clauses, annexures, tables, figures and pages.

    Boundary:
        This engine detects references only. It does not resolve legal meaning or
        insurance meaning.
    """

    VERSION = "2.0"

    PATTERNS = [
        ("section", re.compile(r"\b(?:Section|Sec\.)\s+[A-Z]?\.?\d+(?:\.\d+)*\b", re.IGNORECASE)),
        ("clause", re.compile(r"\b(?:Clause|Clauses)\s+[A-Z]?\.?\d+(?:\.\d+)*\b", re.IGNORECASE)),
        ("annexure", re.compile(r"\bAnnexure\s+[A-Z0-9IVX]+\b", re.IGNORECASE)),
        ("appendix", re.compile(r"\bAppendix\s+[A-Z0-9IVX]+\b", re.IGNORECASE)),
        ("table", re.compile(r"\b(?:Table|Product Benefit Table)\s*[A-Z0-9IVX.]*\b", re.IGNORECASE)),
        ("figure", re.compile(r"\bFigure\s+[A-Z0-9IVX.]+\b", re.IGNORECASE)),
        ("page", re.compile(r"\bPage\s+\d+\b", re.IGNORECASE)),
    ]

    def extract(
        self,
        text: str,
        *,
        document_id: str,
        page_number: int | None = None,
        start_line: int | None = None,
    ) -> list[CrossReference]:
        references: list[CrossReference] = []
        seen: set[tuple[str, str, int]] = set()
        for ref_type, pattern in self.PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(0).strip()
                key = (ref_type, raw.lower(), match.start())
                if key in seen:
                    continue
                seen.add(key)
                prefix = text[: match.start()]
                local_line = prefix.count("\n") + 1
                absolute_line = (start_line or 1) + local_line - 1
                loc = SourceLocation(
                    document_id=document_id,
                    page_number=page_number,
                    page_label=str(page_number) if page_number else None,
                    start_line=absolute_line,
                    end_line=absolute_line,
                    start_char=match.start(),
                    end_char=match.end(),
                )
                references.append(
                    CrossReference(
                        reference_id=stable_id("xref", f"{document_id}|{ref_type}|{raw}|{absolute_line}|{match.start()}"),
                        reference_type=ref_type,
                        text=raw,
                        normalized_target=raw.lower().replace(" ", "_"),
                        location=loc,
                        resolved=False,
                    )
                )
        return references
