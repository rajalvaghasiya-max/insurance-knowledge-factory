from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from knowledge_domains.health.knowledge_manufacturing.knowledge_block_models import (
    KNOWLEDGE_BLOCK_MANUFACTURING_VERSION,
    KnowledgeBlock,
    KnowledgeBlockContent,
    KnowledgeBlockQuality,
    KnowledgeBlockReferences,
    KnowledgeBlockSource,
    KnowledgeBlockStructure,
    stable_id,
)


class KnowledgeBlockBuilder:
    """
    Department IV — Knowledge Block Builder v0.1 / Sprint 2B.1

    Responsibility:
        Manufacture self-contained Knowledge Blocks from a certified Processed Document Asset.

    Boundary:
        This engine organizes meaning units. It does not interpret insurance concepts and does
        not manufacture Knowledge Atoms.
    """

    VERSION = KNOWLEDGE_BLOCK_MANUFACTURING_VERSION

    def build(self, processed_document: dict[str, Any]) -> dict[str, Any]:
        document_id = processed_document.get("document_id", "unknown_document")
        processed_asset_id = processed_document.get("asset_id")
        source = processed_document.get("source") or {}
        sections = processed_document.get("sections") or []
        clauses = processed_document.get("clauses") or []
        clause_ids_by_section = self._index_clauses_by_section(clauses)

        blocks: list[KnowledgeBlock] = []
        warnings: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        duplicate_blocks = 0

        for sequence, section in enumerate(sections, start=1):
            text = self._clean_text(str(section.get("text") or ""))
            title = self._clean_text(str(section.get("title") or ""))
            if not text and not title:
                warnings.append({
                    "type": "empty_section_skipped",
                    "severity": "low",
                    "section_id": section.get("section_id"),
                    "message": "Section had no title or text and was skipped.",
                })
                continue

            block_type = self._classify_block(section, text, title)
            source_location = section.get("source_location") or {}
            section_id = section.get("section_id")
            block_id = stable_id(
                "kb",
                "|".join([
                    document_id,
                    str(processed_asset_id),
                    str(section_id),
                    str(sequence),
                    title[:120],
                    text[:160],
                ]),
            )
            if block_id in seen_ids:
                duplicate_blocks += 1
                continue
            seen_ids.add(block_id)

            cross_refs = section.get("cross_references") or []
            source_clause_ids = clause_ids_by_section.get(section_id, [])
            quality_score = self._quality_score(text=text, title=title, source_location=source_location, cross_refs=cross_refs)
            confidence = round(quality_score / 100, 4)
            notes = ["Knowledge Block manufactured from processed document structure. No semantic insurance interpretation performed."]

            block = KnowledgeBlock(
                block_id=block_id,
                block_version="1.0",
                block_type=block_type,
                document_id=document_id,
                processed_document_asset_id=processed_asset_id,
                structure=KnowledgeBlockStructure(
                    sequence=sequence,
                    heading=title or None,
                    sub_heading=self._derive_subheading(text, title),
                    heading_level=section.get("heading_level") or section.get("level"),
                    source_section_type=section.get("section_type"),
                    contains_table=bool(section.get("contains_table")),
                    contains_list=bool(section.get("contains_list")) or self._contains_list(text),
                    contains_numbers=bool(section.get("contains_numbers")) or bool(re.search(r"\b\d+\b", text)),
                    contains_cross_reference=bool(section.get("contains_cross_reference")) or bool(cross_refs),
                    contains_definition=bool(section.get("contains_definition")) or self._looks_like_definition(text, title),
                ),
                content=KnowledgeBlockContent(
                    title=title or None,
                    text=text,
                    tables=[],
                    lists=self._extract_list_lines(text),
                    notes=self._extract_notes(text),
                ),
                source=KnowledgeBlockSource(
                    document_id=document_id,
                    processed_document_asset_id=processed_asset_id,
                    source_document_type=source.get("document_type") or source.get("source_type"),
                    authority_score=source.get("authority_score"),
                    section_id=section_id,
                    section_order=section.get("order"),
                    parent_section=None,
                    page_number=source_location.get("page_number"),
                    page_label=source_location.get("page_label"),
                    start_line=source_location.get("start_line"),
                    end_line=source_location.get("end_line"),
                    start_char=source_location.get("start_char"),
                    end_char=source_location.get("end_char"),
                ),
                references=KnowledgeBlockReferences(
                    cross_references=cross_refs,
                    child_blocks=[],
                    parent_block=None,
                    source_clause_ids=source_clause_ids,
                ),
                quality=KnowledgeBlockQuality(
                    confidence=confidence,
                    quality_score=quality_score,
                    warnings=[],
                ),
                notes=notes,
            )
            blocks.append(block)

        statistics = self._statistics(blocks, sections, warnings, duplicate_blocks)
        return {
            "blocks": blocks,
            "warnings": warnings,
            "statistics": statistics,
            "duplicate_blocks": duplicate_blocks,
            "orphan_paragraphs": statistics["orphan_paragraphs"],
            "tables_attached": statistics["table_blocks"],
            "cross_references_preserved": statistics["cross_references_preserved"],
            "quality_score": statistics["quality_score"],
            "validation_status": "passed" if statistics["critical_warning_count"] == 0 else "warning",
        }

    def _index_clauses_by_section(self, clauses: list[dict[str, Any]]) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}
        for clause in clauses:
            section_id = clause.get("section_id") or (clause.get("source_location") or {}).get("section_id")
            clause_id = clause.get("clause_id")
            if section_id and clause_id:
                index.setdefault(section_id, []).append(clause_id)
        return index

    def _classify_block(self, section: dict[str, Any], text: str, title: str) -> str:
        low = f"{title}\n{text}".lower()
        section_type = str(section.get("section_type") or "").lower()
        if section_type in {"annexure", "metadata", "footer"}:
            return "metadata_block"
        if self._looks_like_contact(low):
            return "contact_block"
        if self._looks_like_definition(text, title):
            return "definition_block"
        if self._looks_like_procedure(low):
            return "procedure_block"
        if self._looks_like_note(low):
            return "note_block"
        if self._looks_like_illustration(low):
            return "illustration_block"
        if self._looks_like_rule(low):
            return "rule_block"
        if section.get("contains_table"):
            return "table_block"
        if title and len(text.split()) <= 8:
            return "heading_block"
        return "paragraph_block"

    def _quality_score(self, *, text: str, title: str, source_location: dict[str, Any], cross_refs: list[dict[str, Any]]) -> float:
        score = 100.0
        if not text and not title:
            score -= 50
        if not source_location.get("start_line") and not source_location.get("page_number"):
            score -= 5
        if len(text) > 4000:
            score -= 5
        if "�" in text or " quali ed " in f" {text.lower()} ":
            score -= 3
        return round(max(0.0, min(100.0, score)), 2)

    def _statistics(self, blocks: list[KnowledgeBlock], sections: list[dict[str, Any]], warnings: list[dict[str, Any]], duplicate_blocks: int) -> dict[str, Any]:
        counts = Counter(block.block_type for block in blocks)
        cross_refs = sum(len(block.references.cross_references) for block in blocks)
        quality_score = round(sum(block.quality.quality_score for block in blocks) / max(1, len(blocks)), 2)
        source_section_ids = {s.get("section_id") for s in sections if s.get("section_id")}
        block_section_ids = {b.source.section_id for b in blocks if b.source.section_id}
        orphan_paragraphs = max(0, len(source_section_ids - block_section_ids))
        critical_warning_count = sum(1 for w in warnings if w.get("severity") == "critical")
        return {
            "source_section_count": len(sections),
            "total_blocks": len(blocks),
            "heading_blocks": counts.get("heading_block", 0),
            "paragraph_blocks": counts.get("paragraph_block", 0),
            "table_blocks": counts.get("table_block", 0),
            "definition_blocks": counts.get("definition_block", 0),
            "procedure_blocks": counts.get("procedure_block", 0),
            "rule_blocks": counts.get("rule_block", 0),
            "note_blocks": counts.get("note_block", 0),
            "illustration_blocks": counts.get("illustration_block", 0),
            "contact_blocks": counts.get("contact_block", 0),
            "metadata_blocks": counts.get("metadata_block", 0),
            "orphan_paragraphs": orphan_paragraphs,
            "duplicate_blocks": duplicate_blocks,
            "warning_count": len(warnings),
            "critical_warning_count": critical_warning_count,
            "cross_references_preserved": cross_refs,
            "quality_score": quality_score,
            "department_boundary": "knowledge_blocks_only_no_semantic_insurance_interpretation",
        }

    def _derive_subheading(self, text: str, title: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) >= 2 and title and lines[0].lower() == title.lower():
            return lines[1][:160]
        return None

    def _extract_list_lines(self, text: str) -> list[str]:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^([a-zA-Z]\.|\d+\.|[ivxlcdm]+\.|[-•])\s+", stripped, flags=re.I):
                lines.append(stripped[:500])
        return lines[:100]

    def _extract_notes(self, text: str) -> list[str]:
        notes = []
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^(note|provided that|subject to|however|except)\b", stripped, flags=re.I):
                notes.append(stripped[:500])
        return notes[:50]

    def _contains_list(self, text: str) -> bool:
        return bool(self._extract_list_lines(text))

    def _looks_like_definition(self, text: str, title: str) -> bool:
        sample = f"{title} {text}".strip()
        return bool(re.search(r"\b(means|refers to|shall mean|is defined as|means and includes)\b", sample, re.I))

    def _looks_like_procedure(self, low: str) -> bool:
        return any(key in low for key in ["procedure", "process", "steps", "cashless claims", "claim notification", "documents required"])

    def _looks_like_rule(self, low: str) -> bool:
        return any(key in low for key in ["provided that", "subject to", "shall apply", "shall not apply", "only if", "conditions shall apply"])

    def _looks_like_note(self, low: str) -> bool:
        return low.strip().startswith("note") or "important note" in low

    def _looks_like_illustration(self, low: str) -> bool:
        return any(key in low for key in ["illustration", "example", "scenario"])

    def _looks_like_contact(self, low: str) -> bool:
        return any(key in low for key in ["grievance", "ombudsman", "email", "@", "address", "contact"])

    def _clean_text(self, text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
