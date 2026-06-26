from __future__ import annotations

from typing import Dict, List

from .pipeline_models import ManufacturingQueue, ManufacturingTask, SourceDistillationReport


_PRIORITY_SCORE = {"high": 3, "medium": 2, "low": 1}


class ManufacturingQueueBuilder:
    """Converts KDE manufacturing opportunities into a normalized task queue."""

    def build(self, reports: List[SourceDistillationReport], concept_id: str) -> ManufacturingQueue:
        grouped: Dict[str, Dict[str, object]] = {}
        for report in reports:
            for opportunity in report.opportunities:
                item = grouped.setdefault(
                    opportunity.asset_type,
                    {
                        "target_department": opportunity.target_department,
                        "priority": opportunity.priority,
                        "reasons": [],
                        "distillation_ids": [],
                        "observation_ids": [],
                    },
                )
                if _PRIORITY_SCORE.get(opportunity.priority, 2) > _PRIORITY_SCORE.get(str(item["priority"]), 2):
                    item["priority"] = opportunity.priority
                item["reasons"].append(opportunity.reason)  # type: ignore[index]
                item["distillation_ids"].append(report.distillation_id)  # type: ignore[index]
                item["observation_ids"].append(report.observation_id)  # type: ignore[index]
        tasks = [
            ManufacturingTask.create(
                concept_id=concept_id,
                asset_type=asset_type,
                target_department=str(data["target_department"]),
                priority=str(data["priority"]),
                reason=" | ".join(sorted(set(data["reasons"]))),  # type: ignore[arg-type]
                source_distillation_ids=list(data["distillation_ids"]),  # type: ignore[arg-type]
                source_observation_ids=list(data["observation_ids"]),  # type: ignore[arg-type]
            )
            for asset_type, data in grouped.items()
        ]
        tasks = sorted(tasks, key=lambda t: (-_PRIORITY_SCORE.get(t.priority, 2), t.asset_type))
        return ManufacturingQueue.create(concept_id, [r.distillation_id for r in reports], tasks)
