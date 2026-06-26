from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_scanner_models import (
    COMPONENT_COLLECTION_CONTRACT_VERSION,
    SCANNER_VERSION,
    ComponentQuality,
    ComponentScannerSignals,
    ComponentSource,
    KnowledgeComponent,
    KnowledgeComponentCollection,
    KnowledgeComponentScannerReport,
    stable_id,
    utc_now,
)


class KnowledgeComponentScanner:
    """
    Department IV — Meaning Manufacturing
    Production Line 1 — Knowledge Component Manufacturing
    Machine 1 — Knowledge Component Scanner v1.0

    Mission:
        Scan a Processed Document Asset and manufacture raw, domain-independent
        Knowledge Components.

    Important boundary:
        This scanner does NOT interpret insurance meaning. It does not decide
        whether something is copay, waiting period, benefit, exclusion, coverage,
        or claim requirement. It only identifies structural components such as
        title, paragraph, list item, table, note, reference, metadata, and noise.

    Next machine:
        Knowledge Component Classifier.
    """

    VERSION = SCANNER_VERSION

    BULLET_RE = re.compile(r"^\s*((\d+\.?)+|[a-zA-Z]\.|[ivxlcdm]+\.|[-•*])\s+", re.I)
    HEADING_RE = re.compile(r"^\s*((section|chapter|annexure|appendix)\s+[A-Z0-9IVXLC.()\-]+|[A-Z]\.?\d*(\s*[–-])?|\d+\.?\s+[A-Z])", re.I)
    REFERENCE_RE = re.compile(r"\b(refer|see|clause\s+\d+|section\s+[A-Z0-9.()]+|annexure\s+[IVXLC0-9A-Z]+|appendix\s+[A-Z0-9]+|table\s+\d*)\b", re.I)
    NOTE_RE = re.compile(r"^\s*(note|important|please note)\b", re.I)
    METADATA_RE = re.compile(r"\b(product\s+name\s*:|product\s+uin\s*:|policy\s+wording|page\s+\d+\s+of\s+\d+)\b", re.I)
    ONLY_PAGE_NOISE_RE = re.compile(r"^\s*(activ one|policy wording|product name:.*uin:.*|\d+)\s*$", re.I)

    def scan(self, processed_document: dict[str, Any], source_asset_path: str | None = None) -> tuple[KnowledgeComponentCollection, KnowledgeComponentScannerReport]:
        document_id = processed_document.get("document_id", "unknown_document")
        processed_asset_id = processed_document.get("asset_id")
        source_meta = processed_document.get("source") or {}
        sections = processed_document.get("sections") or []
        tables = processed_document.get("tables") or []

        components: list[KnowledgeComponent] = []
        warnings: list[dict[str, Any]] = []
        sequence = 1

        for section in sections:
            fragments = self._section_fragments(section)
            for fragment in fragments:
                text = self._clean_text(fragment.get("text") or "")
                if not text:
                    continue
                component_type = self._scan_type(text, fragment, section)
                source = self._source(document_id, processed_asset_id, source_meta, section, fragment)
                component_id = stable_id(
                    "kcomp",
                    "|".join([
                        str(document_id),
                        str(processed_asset_id),
                        str(source.section_id or ""),
                        str(source.start_line or ""),
                        str(sequence),
                        text[:200],
                    ]),
                )
                signals = self._signals(text, fragment, section, component_type)
                components.append(
                    KnowledgeComponent(
                        component_id=component_id,
                        component_version="1.0",
                        component_type=component_type,
                        document_id=document_id,
                        processed_document_asset_id=processed_asset_id,
                        sequence=sequence,
                        text=text,
                        normalized_text=self._normalize(text),
                        title_hint=self._title_hint(text, section, component_type),
                        source=source,
                        signals=signals,
                        quality=ComponentQuality(
                            confidence=self._confidence(component_type, text),
                            quality_score=round(self._confidence(component_type, text) * 100, 2),
                            warnings=[],
                        ),
                        references=self._references(text, source),
                        notes=[
                            "Raw Knowledge Component scanned from processed document. No insurance semantic interpretation performed."
                        ],
                    )
                )
                sequence += 1

        # Preserve standalone table objects from Department III if present.
        for table in tables:
            text = self._table_to_text(table)
            if not text:
                continue
            source = self._table_source(document_id, processed_asset_id, source_meta, table)
            component_id = stable_id(
                "kcomp",
                "|".join([
                    str(document_id),
                    str(processed_asset_id),
                    str(table.get("table_id") or table.get("id") or ""),
                    str(sequence),
                    text[:200],
                ]),
            )
            components.append(
                KnowledgeComponent(
                    component_id=component_id,
                    component_version="1.0",
                    component_type="table",
                    document_id=document_id,
                    processed_document_asset_id=processed_asset_id,
                    sequence=sequence,
                    text=text,
                    normalized_text=self._normalize(text),
                    title_hint=table.get("title") or table.get("caption"),
                    source=source,
                    signals=ComponentScannerSignals(
                        source_kind="table",
                        structural_signal="table_object",
                        is_table_like=True,
                        contains_cross_reference=bool(self.REFERENCE_RE.search(text)),
                        contains_numbers=bool(re.search(r"\d", text)),
                        word_count=len(text.split()),
                    ),
                    quality=ComponentQuality(confidence=1.0, quality_score=100.0, warnings=[]),
                    references=self._references(text, source),
                    notes=[
                        "Table component preserved from processed document table object. "
                        "No insurance semantic interpretation performed."
                    ],
                )
            )
            sequence += 1

        duplicate_count = self._duplicate_count(components)
        noise_count = sum(1 for c in components if c.component_type == "noise")
        xref_count = sum(len(c.references) for c in components)
        stats = self._statistics(components, len(sections), len(tables), duplicate_count, noise_count, xref_count)
        validation = self._validate(components, duplicate_count)
        quality_score = self._quality_score(stats, validation)

        collection_id = stable_id("kcc", f"{document_id}|{processed_asset_id}|{len(components)}|{SCANNER_VERSION}")
        collection = KnowledgeComponentCollection(
            asset_type="knowledge_component_collection",
            collection_id=collection_id,
            collection_version="1.0",
            contract_version=COMPONENT_COLLECTION_CONTRACT_VERSION,
            created_at=utc_now(),
            department="department_04_knowledge_manufacturing",
            production_line="knowledge_component_manufacturing",
            engine="KnowledgeComponentScanner",
            document_id=document_id,
            processed_document_asset_id=processed_asset_id,
            source_asset_path=source_asset_path,
            components=components,
            statistics=stats,
            quality={"quality_score": quality_score, "scanner_version": SCANNER_VERSION},
            validation=validation,
            status="manufactured" if validation.get("status") == "passed" else "manufactured_with_warnings",
            next_stage="knowledge_component_classification",
        )

        report = KnowledgeComponentScannerReport(
            report_type="knowledge_component_scanner_report",
            report_id=stable_id("kcsr", f"{collection_id}|{utc_now()}"),
            report_version="1.0",
            created_at=utc_now(),
            department="department_04_knowledge_manufacturing",
            production_line="knowledge_component_manufacturing",
            engine="KnowledgeComponentScanner",
            document_id=document_id,
            processed_document_asset_id=processed_asset_id,
            collection_id=collection_id,
            collection_path=None,
            components_created=len(components),
            source_sections_processed=len(sections),
            source_tables_processed=len(tables),
            duplicate_components=duplicate_count,
            noise_components=noise_count,
            cross_references_preserved=xref_count,
            warnings=warnings + validation.get("warnings", []),
            quality_score=quality_score,
            validation_status=validation.get("status", "unknown"),
            statistics=stats,
            next_stage="knowledge_component_classification",
        )
        return collection, report

    def _section_fragments(self, section: dict[str, Any]) -> list[dict[str, Any]]:
        """Turn a processed-document section into raw scan fragments.

        We keep this intentionally conservative: paragraphs separated by blank
        lines become fragments; bullet/list lines become their own fragments;
        headings stay attached as title candidates. Composition happens later.
        """
        text = section.get("text") or section.get("content") or ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.rstrip() for ln in text.split("\n")]

        fragments: list[dict[str, Any]] = []
        buffer: list[str] = []
        start_line = section.get("source", {}).get("start_line") or section.get("start_line")
        current_start = start_line

        def flush(end_offset: int) -> None:
            nonlocal buffer, current_start
            if buffer:
                fragments.append({
                    "text": "\n".join(buffer).strip(),
                    "start_line": current_start,
                    "end_line": (start_line + end_offset) if isinstance(start_line, int) else None,
                    "source_kind": "section_fragment",
                })
                buffer = []
                current_start = None

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                flush(idx)
                continue
            line_no = (start_line + idx) if isinstance(start_line, int) else None
            if current_start is None:
                current_start = line_no

            # List-like lines are separate raw components unless continuing a long wrapped line.
            if self.BULLET_RE.match(stripped):
                flush(max(idx - 1, 0))
                fragments.append({
                    "text": stripped,
                    "start_line": line_no,
                    "end_line": line_no,
                    "source_kind": "list_line",
                })
                current_start = None
            else:
                buffer.append(stripped)
        flush(len(lines))

        if not fragments and text.strip():
            fragments.append({"text": text.strip(), "start_line": start_line, "end_line": section.get("source", {}).get("end_line") or section.get("end_line"), "source_kind": "section"})
        return fragments

    def _scan_type(self, text: str, fragment: dict[str, Any], section: dict[str, Any]) -> str:
        if self.ONLY_PAGE_NOISE_RE.match(text):
            return "noise"
        if self.METADATA_RE.search(text):
            # If metadata is mixed with real content, keep as paragraph; classifier can split later.
            if len(text.split()) <= 12:
                return "metadata"
        if fragment.get("source_kind") == "list_line" or self.BULLET_RE.match(text):
            return "list_item"
        if self.NOTE_RE.search(text):
            return "note"
        if self.REFERENCE_RE.search(text) and len(text.split()) <= 18:
            return "reference"
        if self._looks_like_title(text, section):
            return "title"
        return "paragraph"

    def _looks_like_title(self, text: str, section: dict[str, Any]) -> bool:
        compact = " ".join(text.split())
        if len(compact) > 140:
            return False
        if self.HEADING_RE.match(compact):
            return True
        if compact.endswith(":") and len(compact.split()) <= 14:
            return True
        if section.get("title") and compact == str(section.get("title")).strip():
            return True
        return False

    def _source(self, document_id: str, processed_asset_id: str | None, source_meta: dict[str, Any], section: dict[str, Any], fragment: dict[str, Any]) -> ComponentSource:
        src = section.get("source") or {}
        return ComponentSource(
            document_id=document_id,
            processed_document_asset_id=processed_asset_id,
            source_document_type=source_meta.get("source_document_type") or source_meta.get("document_type") or source_meta.get("source_type"),
            authority_score=source_meta.get("authority_score"),
            section_id=section.get("section_id") or section.get("id"),
            section_order=section.get("order") or section.get("section_order") or src.get("section_order"),
            page_number=src.get("page_number") or section.get("page_number"),
            page_label=src.get("page_label") or section.get("page_label"),
            start_line=fragment.get("start_line") or src.get("start_line"),
            end_line=fragment.get("end_line") or src.get("end_line"),
            start_char=fragment.get("start_char") or src.get("start_char"),
            end_char=fragment.get("end_char") or src.get("end_char"),
        )

    def _table_source(self, document_id: str, processed_asset_id: str | None, source_meta: dict[str, Any], table: dict[str, Any]) -> ComponentSource:
        src = table.get("source") or {}
        return ComponentSource(
            document_id=document_id,
            processed_document_asset_id=processed_asset_id,
            source_document_type=source_meta.get("source_document_type") or source_meta.get("document_type") or source_meta.get("source_type"),
            authority_score=source_meta.get("authority_score"),
            section_id=table.get("section_id") or src.get("section_id"),
            section_order=src.get("section_order"),
            page_number=src.get("page_number") or table.get("page_number"),
            page_label=src.get("page_label") or table.get("page_label"),
            start_line=src.get("start_line"),
            end_line=src.get("end_line"),
        )

    def _signals(self, text: str, fragment: dict[str, Any], section: dict[str, Any], component_type: str) -> ComponentScannerSignals:
        return ComponentScannerSignals(
            source_kind=fragment.get("source_kind"),
            structural_signal=component_type,
            is_heading_like=component_type == "title",
            is_list_like=component_type == "list_item",
            is_table_like=component_type == "table",
            is_metadata_like=component_type == "metadata",
            is_noise_like=component_type == "noise",
            contains_cross_reference=bool(self.REFERENCE_RE.search(text)),
            contains_numbers=bool(re.search(r"\d", text)),
            paragraph_count=max(1, len([p for p in re.split(r"\n\s*\n", text) if p.strip()])),
            word_count=len(text.split()),
        )

    def _references(self, text: str, source: ComponentSource) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for match in self.REFERENCE_RE.finditer(text):
            ref_text = match.group(0).strip()
            refs.append({
                "reference_id": stable_id("xref", f"{source.document_id}|{source.start_line}|{match.start()}|{ref_text}"),
                "text": ref_text,
                "normalized_target": self._normalize(ref_text).replace(" ", "_"),
                "start_char": match.start(),
                "end_char": match.end(),
                "resolved": False,
            })
        return refs

    def _title_hint(self, text: str, section: dict[str, Any], component_type: str) -> str | None:
        if component_type == "title":
            return " ".join(text.split())[:160]
        heading = section.get("title") or section.get("heading")
        if heading:
            return str(heading)[:160]
        return None

    def _table_to_text(self, table: dict[str, Any]) -> str:
        if table.get("text"):
            return self._clean_text(str(table["text"]))
        rows = table.get("rows") or []
        if not rows:
            return ""
        lines = []
        for row in rows:
            if isinstance(row, list):
                lines.append(" | ".join(str(cell) for cell in row))
            elif isinstance(row, dict):
                lines.append(" | ".join(str(v) for v in row.values()))
            else:
                lines.append(str(row))
        return self._clean_text("\n".join(lines))

    def _duplicate_count(self, components: list[KnowledgeComponent]) -> int:
        seen: set[str] = set()
        duplicates = 0
        for comp in components:
            key = comp.normalized_text
            if key in seen:
                duplicates += 1
            seen.add(key)
        return duplicates

    def _statistics(self, components: list[KnowledgeComponent], section_count: int, table_count: int, duplicate_count: int, noise_count: int, xref_count: int) -> dict[str, Any]:
        counts = Counter(c.component_type for c in components)
        words = [c.signals.word_count for c in components]
        return {
            "source_section_count": section_count,
            "source_table_count": table_count,
            "total_components": len(components),
            "component_type_counts": dict(counts),
            "title_components": counts.get("title", 0),
            "paragraph_components": counts.get("paragraph", 0),
            "list_item_components": counts.get("list_item", 0),
            "table_components": counts.get("table", 0),
            "note_components": counts.get("note", 0),
            "reference_components": counts.get("reference", 0),
            "metadata_components": counts.get("metadata", 0),
            "noise_components": noise_count,
            "duplicate_components": duplicate_count,
            "cross_references_preserved": xref_count,
            "average_words_per_component": round(sum(words) / len(words), 2) if words else 0,
            "max_words_per_component": max(words) if words else 0,
            "department_boundary": "raw_components_only_no_semantic_insurance_interpretation",
        }

    def _validate(self, components: list[KnowledgeComponent], duplicate_count: int) -> dict[str, Any]:
        warnings: list[dict[str, Any]] = []
        ids = [c.component_id for c in components]
        missing_source = [c.component_id for c in components if not c.source.section_id and c.component_type != "table"]
        if len(ids) != len(set(ids)):
            warnings.append({"type": "duplicate_component_id", "severity": "critical", "message": "Duplicate component IDs detected."})
        if missing_source:
            warnings.append({"type": "missing_source", "severity": "medium", "message": f"{len(missing_source)} components have incomplete section provenance."})
        if duplicate_count:
            warnings.append({"type": "duplicate_text", "severity": "low", "message": f"{duplicate_count} duplicate component texts detected."})
        status = "passed" if not any(w.get("severity") == "critical" for w in warnings) else "failed"
        return {
            "status": status,
            "component_count": len(components),
            "unique_component_ids": len(set(ids)),
            "warnings": warnings,
        }

    def _quality_score(self, stats: dict[str, Any], validation: dict[str, Any]) -> float:
        score = 100.0
        if validation.get("status") == "failed":
            score -= 30
        score -= min(10.0, stats.get("duplicate_components", 0) * 0.02)
        score -= min(5.0, stats.get("noise_components", 0) * 0.01)
        return round(max(0.0, score), 2)

    def _confidence(self, component_type: str, text: str) -> float:
        if component_type == "noise":
            return 0.5
        if component_type in {"title", "table", "list_item", "metadata"}:
            return 0.95
        return 0.9

    def _clean_text(self, text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()


class KnowledgeComponentScannerRunner:
    """File-oriented runner used by scripts/run_knowledge_component_scanner.py."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "knowledge" / "factory" / "knowledge_components"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scanner = KnowledgeComponentScanner()

    def run(self, processed_document_path: str | Path) -> dict[str, Any]:
        processed_path = Path(processed_document_path)
        if not processed_path.is_absolute():
            processed_path = self.project_root / processed_path
        if not processed_path.exists():
            raise FileNotFoundError(f"Processed document not found: {processed_path}")

        processed_document = json.loads(processed_path.read_text(encoding="utf-8"))
        collection, report = self.scanner.scan(processed_document, source_asset_path=str(processed_document_path))

        base = f"{collection.document_id}_{collection.processed_document_asset_id}_{collection.collection_id}"
        collection_path = self.output_dir / f"{base}_knowledge_component_collection.json"
        report_path = self.output_dir / f"{base}_knowledge_component_scanner_report.json"
        report.collection_path = str(collection_path)

        collection_path.write_text(json.dumps(collection.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        report_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "collection": collection,
            "report": report,
            "collection_path": collection_path,
            "report_path": report_path,
        }
