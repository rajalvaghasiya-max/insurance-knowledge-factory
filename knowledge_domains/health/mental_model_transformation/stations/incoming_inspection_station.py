from __future__ import annotations

from typing import Any, Dict
from ..transformation_blueprint import TransformationBlueprint


class IncomingInspectionStation:
    """Validates that a distillation report can enter MMTC."""

    def inspect(self, report: Dict[str, Any]) -> Dict[str, Any]:
        observation = report.get("observation", {})
        opportunities = [o.get("asset_type") for o in report.get("manufacturing_opportunities", [])]
        checks = {
            "has_distillation_id": bool(report.get("distillation_id")),
            "has_observation": bool(observation),
            "has_concept_id": bool(observation.get("concept_id")),
            "requests_mental_model_asset": "mental_model_asset" in opportunities,
        }
        return {
            "pass": all(checks.values()),
            "checks": checks,
            "opportunities": opportunities,
        }

    def manufacture(self, report: Dict[str, Any]) -> TransformationBlueprint:
        inspection = self.inspect(report)
        observation = report.get("observation", {})
        blueprint = TransformationBlueprint(
            concept_id=observation.get("concept_id", "unknown"),
            concept_name=observation.get("concept_id", "unknown").replace("_", " ").title(),
            source_distillation_id=report.get("distillation_id", "unknown"),
            source_observation_id=observation.get("observation_id", "unknown"),
            source_report=report,
            inspection=inspection,
            status="inspection_passed" if inspection["pass"] else "inspection_failed",
        )
        blueprint.log("incoming_inspection_station")
        return blueprint
