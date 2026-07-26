from __future__ import annotations

from ..concept_profiles import get_concept_profile
from ..mental_model_models import BehaviourGoal
from ..transformation_blueprint import TransformationBlueprint


class BehaviourGoalStation:
    """Manufactures observable behaviour goals that prove the transformation worked."""

    def manufacture(self, blueprint: TransformationBlueprint) -> TransformationBlueprint:
        profile = get_concept_profile(blueprint.concept_id)

        if profile:
            blueprint.behaviour_goal = BehaviourGoal(
                profile.expected_question,
                profile.expected_behaviour,
                profile.observable_success,
            )
            blueprint.status = "behaviour_goal_built"
            blueprint.log("behaviour_goal_station")
            return blueprint

        missing = set(
            blueprint.knowledge_gap.missing_concepts
            if blueprint.knowledge_gap
            else []
        )

        if "admissible_claim" in missing:
            q = "Is Copay calculated on the admissible claim amount or on the hospital bill?"
            b = "Customer asks for a mock claim calculation before buying or claiming."
            success = "Customer calculates Copay correctly using approved amount in a scenario."

        elif "treatment_zone" in missing:
            q = "Which city or hospital would we use for a major medical emergency?"
            b = "Customer checks zone terms before selecting the cheaper premium."
            success = "Customer compares premium saving against potential zone Copay liability."

        else:
            q = "What is the claim-stage consequence of this term?"
            b = "Customer asks for consequence before choosing price benefit."
            success = "Customer can state one practical decision impact."

        blueprint.behaviour_goal = BehaviourGoal(q, b, success)
        blueprint.status = "behaviour_goal_built"
        blueprint.log("behaviour_goal_station")
        return blueprint