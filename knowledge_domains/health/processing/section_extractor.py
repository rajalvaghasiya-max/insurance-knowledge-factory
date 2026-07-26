from __future__ import annotations

import re

from .cross_reference_extractor import CrossReferenceExtractionEngine
from .processing_models import ProcessedSection, SourceLocation, stable_id


class SectionExtractionEngine:
    """
    Department III — Document Processing
    Engine: Section Extraction Engine v2.0

    Responsibility:
        Split normalized text into structural sections and enrich document structure.

    Boundary:
        This engine classifies document structure, not insurance meaning.
    """

    VERSION = "2.0"

    HEADING_PATTERNS = [
        re.compile(r"^\s*(?:Section\s+)?[A-Z](?:\.\d+)*(?:\.|\s|–|-)\s*.{3,140}$", re.IGNORECASE),
        re.compile(r"^\s*(?:Section\s+)?\d+(?:\.\d+)*[\).:-]?\s+.{3,140}$", re.IGNORECASE),
        re.compile(r"^\s*[A-Z][A-Z0-9 &,/()\-]{6,140}$"),
        re.compile(r"^\s*(?:part|chapter|schedule|annexure|appendix)\s+[A-Z0-9IVX]+\b.{0,120}$", re.IGNORECASE),
        re.compile(r"^\s*[A-Z]\.\d+(?:\.\d+)*\s+.{3,140}$", re.IGNORECASE),
    ]

    def __init__(self) -> None:
        self.cross_ref_extractor = CrossReferenceExtractionEngine()

    def extract(self, text: str, *, document_id: str) -> list[ProcessedSection]:
        lines = text.splitlines()
        headings: list[tuple[int, str]] = []

        for idx, line in enumerate(lines):
            candidate = line.strip()
            if not candidate:
                continue
            if self.is_heading(candidate):
                headings.append((idx, candidate))

        if not headings:
            return [self.build_section(document_id, 1, "Full Document", 0, len(lines), text, 1)]

        sections: list[ProcessedSection] = []
        for order, (start_idx, title) in enumerate(headings, start=1):
            end_idx = headings[order][0] if order < len(headings) else len(lines)
            section_text = "\n".join(lines[start_idx:end_idx]).strip()
            if not section_text:
                continue
            sections.append(self.build_section(document_id, order, title, start_idx, end_idx, section_text, self.estimate_level(title)))

        return sections

    def build_section(
        self,
        document_id: str,
        order: int,
        title: str,
        start_idx: int,
        end_idx: int,
        section_text: str,
        level: int,
    ) -> ProcessedSection:
        start_line = start_idx + 1
        end_line = end_idx
        section_id = stable_id("sec", f"{document_id}|{title.lower()}|{start_line}|{end_line}")
        loc = SourceLocation(document_id=document_id, start_line=start_line, end_line=end_line)
        cross_refs = self.cross_ref_extractor.extract(section_text, document_id=document_id, start_line=start_line)
        return ProcessedSection(
            section_id=section_id,
            title=title,
            level=level,
            order=order,
            text=section_text,
            char_count=len(section_text),
            word_count=len(section_text.split()),
            line_count=len(section_text.splitlines()),
            source_location=loc,
            section_type=self.classify_section_type(title, section_text),
            heading_level=level,
            contains_table=self.contains_table_like_content(section_text),
            contains_list=self.contains_list(section_text),
            contains_numbers=bool(re.search(r"\d", section_text)),
            contains_cross_reference=bool(cross_refs),
            contains_definition=self.contains_definition(section_text),
            cross_references=cross_refs,
            confidence=self.estimate_confidence(title, section_text),
        )

    def is_heading(self, line: str) -> bool:
        if len(line) < 4 or len(line) > 160:
            return False
        if line.count(".") > 5 and not re.match(r"^\s*(?:[A-Z]\.)?\d+(?:\.\d+)*", line):
            return False
        return any(pattern.match(line) for pattern in self.HEADING_PATTERNS)

    def estimate_level(self, title: str) -> int:
        match = re.match(r"^\s*(?:Section\s+)?([A-Z]?\.?\d+(?:\.\d+)*)", title, re.IGNORECASE)
        if match:
            return min(1 + match.group(1).count("."), 6)
        if re.match(r"^\s*(annexure|appendix|chapter|part)\b", title, re.IGNORECASE):
            return 1
        return 2 if title[:1].isupper() else 1

    def classify_section_type(self, title: str, text: str) -> str:
        joined = f"{title}\n{text[:500]}".lower()
        if re.search(r"\bannexure\b", joined):
            return "annexure"
        if re.search(r"\bappendix\b", joined):
            return "appendix"
        if re.search(r"\bdefinition|means\b", joined):
            return "definition_block"
        if re.search(r"\bexclusion|excluded\b", joined):
            return "exclusion_block"
        if re.search(r"\bclaim|cashless|reimbursement|pre-authori", joined):
            return "procedure_block"
        if self.contains_table_like_content(text):
            return "table_block"
        if re.search(r"\bbenefit|cover|coverage\b", joined):
            return "coverage_block"
        if re.search(r"\bterms|condition|clause\b", joined):
            return "legal_block"
        return "section"

    def contains_table_like_content(self, text: str) -> bool:
        table_like = 0
        for line in text.splitlines():
            stripped = line.strip()
            if "|" in stripped or re.search(r"\S\s{2,}\S", stripped):
                table_like += 1
        return table_like >= 2

    def contains_list(self, text: str) -> bool:
        return bool(re.search(r"(?m)^\s*(?:[a-zA-Z0-9]+[\).]|[•\-–])\s+", text))

    def contains_definition(self, text: str) -> bool:
        return bool(re.search(r"\bmeans\b|\bshall mean\b|\brefers to\b", text, re.IGNORECASE))

    def estimate_confidence(self, title: str, text: str) -> float:
        score = 0.75
        if title and len(title) <= 160:
            score += 0.1
        if len(text) > 20:
            score += 0.1
        if self.contains_list(text) or self.contains_table_like_content(text):
            score += 0.03
        return min(1.0, round(score, 3))
