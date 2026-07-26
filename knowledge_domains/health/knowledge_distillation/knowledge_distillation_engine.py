from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .distillation_models import DistillationReport
from .knowledge_potential_engine import KnowledgePotentialEngine
from .observation_classifier import ObservationClassifier
from .observation_models import ObservationRecord
from .opportunity_detector import OpportunityDetector
from .relationship_detector import RelationshipDetector


class KnowledgeDistillationEngine:
    """Orchestrates deterministic distillation of observations into production plans."""

    def __init__(self) -> None:
        self.classifier = ObservationClassifier()
        self.potential = KnowledgePotentialEngine()
        self.opportunities = OpportunityDetector()
        self.relationships = RelationshipDetector()

    def distill(self, observation: ObservationRecord) -> DistillationReport:
        classification = self.classifier.classify(observation)
        score = self.potential.score(observation)
        opportunities = self.opportunities.detect(observation, classification["detected_signals"])
        relationships = self.relationships.detect(observation)
        confidence = self._confidence(observation, score.overall, classification["needs_human_review"])
        review_required = confidence < 0.9 or score.overall >= 8.0
        return DistillationReport.create(
            observation=observation,
            classification=classification,
            knowledge_potential=score,
            opportunities=opportunities,
            relationships=relationships,
            confidence=confidence,
            review_required=review_required,
        )

    def distill_many(self, observations: List[ObservationRecord]) -> List[DistillationReport]:
        return [self.distill(obs) for obs in observations]

    def write_reports(self, reports: List[DistillationReport], output_dir: str | Path) -> List[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []
        for report in reports:
            path = output_dir / f"{report.distillation_id}_distillation_report.json"
            with path.open("w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            paths.append(path)
        return paths

    def _confidence(self, observation: ObservationRecord, kps: float, needs_human_review: bool) -> float:
        base = 0.72
        if observation.confidence.lower() in {"very high", "high"}:
            base += 0.15
        elif observation.confidence.lower() == "low":
            base -= 0.10
        if observation.source.lower() not in {"unknown", ""}:
            base += 0.05
        if kps >= 8:
            base += 0.05
        if needs_human_review:
            base -= 0.05
        return round(max(0.0, min(0.99, base)), 2)
