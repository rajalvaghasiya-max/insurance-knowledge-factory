from __future__ import annotations

from ..concept_profiles import get_concept_profile
from ..mental_model_models import TransformationPlan
from ..transformation_blueprint import TransformationBlueprint


class TransformationPlanningStation:
    """Creates deterministic transformation steps from current model to target model."""

    def manufacture(self, blueprint: TransformationBlueprint) -> TransformationBlueprint:
        profile = get_concept_profile(blueprint.concept_id)

        if profile:
            blueprint.transformation_plan = TransformationPlan(
                transformation_type=profile.transformation_type,
                steps=profile.transformation_steps,
                recommended_examples=profile.recommended_examples,
                golden_rule=profile.golden_rule,
            )
            blueprint.status = "transformation_planned"
            blueprint.log("transformation_planning_station")
            return blueprint

        gap = blueprint.knowledge_gap
        missing = set(gap.missing_concepts if gap else [])

        if "admissible_claim" in missing:
            t_type = "Correction"
            steps = [
                "Expose the misconception: customer is calculating Copay on the hospital bill.",
                "Introduce the missing concept: admissible claim amount.",
                "Show the claim sequence: bill -> deductions -> admissible claim -> Copay.",
                "Use a realistic financial example.",
                "Verify with a numerical scenario.",
            ]
            examples = ["₹5,00,000 bill, ₹4,50,000 approved, 10% Copay"]
            golden_rule = (
                "Never calculate Copay on the hospital bill; calculate it on the admissible claim amount."
            )

        elif "treatment_zone" in missing:
            t_type = "Contextualization"
            steps = [
                "Explain that premium zone and treatment zone can differ.",
                "Show the cash impact of taking treatment in a higher-cost city.",
                "Ask where the family would actually go for major treatment.",
                "Verify whether the cheaper premium is worth the claim-stage risk.",
            ]
            examples = ["Zone C policy with treatment in Mumbai or Delhi"]
            golden_rule = (
                "Choose policy zone based on where you may take treatment, not only where you live today."
            )

        else:
            t_type = "Expansion"
            steps = [
                "Clarify the incomplete model.",
                "Connect the missing concept.",
                "Verify with a scenario.",
            ]
            examples = ["Concept-specific scenario"]
            golden_rule = (
                "Understand the claim-stage consequence before choosing the premium benefit."
            )

        blueprint.transformation_plan = TransformationPlan(
            transformation_type=t_type,
            steps=steps,
            recommended_examples=examples,
            golden_rule=golden_rule,
        )
        blueprint.status = "transformation_planned"
        blueprint.log("transformation_planning_station")
        return blueprint