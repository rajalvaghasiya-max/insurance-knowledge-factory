from __future__ import annotations

from ..concept_profiles import get_concept_profile
from ..mental_model_models import TargetMentalModel
from ..transformation_blueprint import TransformationBlueprint


class TargetModelStation:
    """Builds the decision-ready target mental model."""

    def manufacture(self, blueprint: TransformationBlueprint) -> TransformationBlueprint:
        profile = get_concept_profile(blueprint.concept_id)

        if profile:
            belief = profile.target_belief
            reasoning = profile.target_reasoning
            implication = profile.decision_implication

        elif blueprint.concept_id == "copay":
            belief = (
                "Insurance first determines the admissible claim amount after policy conditions, "
                "deductions, and exclusions. Copay applies to that admissible amount, while rejected "
                "items remain fully payable by the customer."
            )
            reasoning = "Copay is a claim-sharing rule applied after claim admissibility is determined."
            implication = "The customer can estimate realistic out-of-pocket cash before buying or claiming."

        else:
            belief = "The customer understands the concept in its policy and decision context."
            reasoning = "Target model derived from certified understanding asset."
            implication = "The customer can make an informed decision."

        blueprint.target_model = TargetMentalModel(
            belief=belief,
            reasoning=reasoning,
            decision_implication=implication,
        )
        blueprint.status = "target_model_built"
        blueprint.log("target_model_station")
        return blueprint