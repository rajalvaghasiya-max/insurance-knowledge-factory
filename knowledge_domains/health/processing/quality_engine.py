from __future__ import annotations

from typing import Any

from .processing_models import ProcessedDocumentAsset, QualityScores


class ProcessedDocumentQualityEngine:
    """
    Department III — Document Processing
    Engine: Processed Document Quality Engine

    Responsibility:
        Compute quality metrics for Processed Document Assets.
    """

    VERSION = "2.0"

    def score(self, asset: ProcessedDocumentAsset, validation_result: dict[str, Any] | None = None) -> QualityScores:
        notes: list[str] = []
        identity_score = 100.0 if asset.asset_id and all(self.has_ids(asset)) else 85.0
        provenance_score = self.provenance_score(asset)
        structure_score = self.structure_score(asset)
        validation_score = 100.0 if validation_result is None or validation_result.get("status") == "passed" else 70.0
        warning_score = self.warning_score(asset)
        completeness_score = self.completeness_score(asset)

        overall = round(
            identity_score * 0.15
            + provenance_score * 0.20
            + structure_score * 0.20
            + validation_score * 0.15
            + warning_score * 0.10
            + completeness_score * 0.20,
            2,
        )

        if overall < 95:
            notes.append("Overall score below Department III preferred handover threshold of 95")
        if any(w.severity == "critical" for w in asset.warnings):
            notes.append("Critical warning present")

        return QualityScores(
            overall_score=overall,
            identity_score=round(identity_score, 2),
            provenance_score=round(provenance_score, 2),
            structure_score=round(structure_score, 2),
            validation_score=round(validation_score, 2),
            warning_score=round(warning_score, 2),
            completeness_score=round(completeness_score, 2),
            notes=notes,
        )

    def has_ids(self, asset: ProcessedDocumentAsset):
        yield from (bool(page.page_id) for page in asset.pages)
        yield from (bool(section.section_id) for section in asset.sections)
        yield from (bool(table.table_id) for table in asset.tables)
        yield from (bool(clause.clause_id) for clause in asset.clauses)

    def provenance_score(self, asset: ProcessedDocumentAsset) -> float:
        items = [*asset.pages, *asset.sections, *asset.tables, *asset.clauses]
        if not items:
            return 0.0
        valid = 0
        for item in items:
            loc = getattr(item, "source_location", None)
            if loc and loc.document_id == asset.document_id:
                valid += 1
        return 100.0 * valid / len(items)

    def structure_score(self, asset: ProcessedDocumentAsset) -> float:
        score = 0.0
        if asset.pages:
            score += 35
        if asset.sections:
            score += 35
        if asset.clauses:
            score += 15
        if asset.tables:
            score += 10
        if asset.cross_references is not None:
            score += 5
        return min(100.0, score)

    def warning_score(self, asset: ProcessedDocumentAsset) -> float:
        score = 100.0
        for warning in asset.warnings:
            if warning.severity == "critical":
                score -= 40
            elif warning.severity == "high":
                score -= 20
            elif warning.severity == "medium":
                score -= 10
            elif warning.severity == "low":
                score -= 4
        return max(0.0, score)

    def completeness_score(self, asset: ProcessedDocumentAsset) -> float:
        stats = asset.statistics or {}
        score = 0.0
        if stats.get("char_count", 0) > 0:
            score += 25
        if stats.get("word_count", 0) > 0:
            score += 20
        if stats.get("line_count", 0) > 0:
            score += 15
        if stats.get("page_count", 0) > 0:
            score += 15
        if stats.get("section_count", 0) > 0:
            score += 15
        if "processing_time_ms" in stats:
            score += 10
        return min(100.0, score)
