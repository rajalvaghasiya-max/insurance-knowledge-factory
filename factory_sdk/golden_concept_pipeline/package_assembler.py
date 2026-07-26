from __future__ import annotations

from typing import List

from .pipeline_models import GoldenConceptPackage, ManufacturingQueue, SourceDistillationReport


class PackageAssembler:
    """Assembles the Golden Concept Package manifest from planned tasks."""

    def assemble(self, concept_id: str, reports: List[SourceDistillationReport], queue: ManufacturingQueue) -> GoldenConceptPackage:
        return GoldenConceptPackage.create(concept_id, reports, queue)
