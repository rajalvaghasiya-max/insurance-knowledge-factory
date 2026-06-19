from __future__ import annotations

import re

from .cross_reference_extractor import CrossReferenceExtractionEngine
from .processing_models import ProcessedClause, SourceLocation, stable_id


class ClauseExtractionEngine:
    """
    Department III — Document Processing
    Engine: Clause Extraction Engine v2.0

    Responsibility:
        Identify numbered/bulleted clauses as document structure only.
    """

    VERSION = "2.0"

    CLAUSE_PATTERN = re.compile(
        r"^\s*((?:[A-Z]\.)?\d+(?:\.\d+)*|[a-zA-Z]|[ivxlcdmIVXLCDM]+)[\).]\s+(.{3,})$"
    )

    def __init__(self) -> None:
        self.cross_ref_extractor = CrossReferenceExtractionEngine()

    def extract(self, text: str, *, document_id: str) -> list[ProcessedClause]:
        clauses: list[ProcessedClause] = []
        for idx, line in enumerate(text.splitlines()):
            stripped = line.strip()
            match = self.CLAUSE_PATTERN.match(stripped)
            if not match:
                continue
            number = match.group(1).rstrip(").")
            clause_text = match.group(2).strip()
            order = len(clauses) + 1
            loc = SourceLocation(document_id=document_id, start_line=idx + 1, end_line=idx + 1)
            cross_refs = self.cross_ref_extractor.extract(clause_text, document_id=document_id, start_line=idx + 1)
            clauses.append(
                ProcessedClause(
                    clause_id=stable_id("cls", f"{document_id}|{idx+1}|{number}|{clause_text[:100]}"),
                    order=order,
                    clause_number=number,
                    text=clause_text,
                    char_count=len(clause_text),
                    source_location=loc,
                    extraction_method="heuristic_clause_v2",
                    cross_references=cross_refs,
                    confidence=0.85 if number else 0.65,
                )
            )
        return clauses
