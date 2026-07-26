from __future__ import annotations

from ..mental_model_models import CurrentMentalModel
from ..transformation_blueprint import TransformationBlueprint


class CurrentModelDetectionStation:
    """Detects the incorrect or incomplete customer belief from the source observation."""

    def manufacture(self, blueprint: TransformationBlueprint) -> TransformationBlueprint:
        obs = blueprint.source_report.get("observation", {})
        text = (obs.get("observation") or "").lower()
        title = (obs.get("title") or "").lower()

        if blueprint.concept_id == "copay" and ("total hospital bill" in text or "total hospital bill" in title):
            belief = "Insurance pays a fixed percentage of the total hospital bill."
            misconceptions = [
                "Copay is calculated on the hospital bill.",
                "Non-medical deductions do not matter while calculating Copay.",
                "Policy conditions are applied after Copay rather than before it.",
            ]
        elif blueprint.concept_id == "copay" and "zone" in text:
            belief = "A cheaper zone policy only changes premium, not claim-stage cash liability."
            misconceptions = [
                "Treatment city will not affect Copay.",
                "Home address zone is enough for buying decision.",
            ]
        else:
            belief = obs.get("title") or "Customer has an incomplete mental model."
            misconceptions = [obs.get("observation", "")]

        blueprint.current_model = CurrentMentalModel(
            belief=belief,
            confidence=obs.get("confidence", "medium"),
            origin=obs.get("source", "unknown"),
            common_misconceptions=[m for m in misconceptions if m],
        )
        blueprint.status = "current_model_detected"
        blueprint.log("current_model_detection_station")
        return blueprint
