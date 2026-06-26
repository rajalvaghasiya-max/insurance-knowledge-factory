from __future__ import annotations

from typing import Any, Dict
from ..mental_model_models import MentalModelAsset


class QualityStation:
    def inspect(self, asset: MentalModelAsset) -> Dict[str, Any]:
        checks = {
            "current_model_present": bool(asset.current_mental_model and asset.current_mental_model.belief),
            "target_model_present": bool(asset.target_mental_model and asset.target_mental_model.belief),
            "gap_present": bool(asset.knowledge_gap and asset.knowledge_gap.missing_concepts),
            "transformation_type_present": bool(asset.transformation_plan and asset.transformation_plan.transformation_type),
            "decision_readiness_present": bool(asset.decision_readiness and asset.decision_readiness.customer_can),
            "behaviour_goal_present": bool(asset.behaviour_goal and asset.behaviour_goal.expected_behaviour),
            "verification_present": bool(asset.verification and asset.verification.question),
            "traceability_present": bool(asset.evidence_traceability.get("distillation_report")),
        }
        return {
            "pass": all(checks.values()),
            "checks": checks,
        }
