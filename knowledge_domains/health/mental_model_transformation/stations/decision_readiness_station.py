from __future__ import annotations

from ..concept_profiles import get_concept_profile
from ..mental_model_models import DecisionReadiness
from ..transformation_blueprint import TransformationBlueprint


class DecisionReadinessStation:
    """Defines what the customer can do after the transformation succeeds."""

    def manufacture(self, blueprint: TransformationBlueprint) -> TransformationBlueprint:
        profile = get_concept_profile(blueprint.concept_id)

        if profile:
            blueprint.decision_readiness = DecisionReadiness(
                profile.customer_can,
                profile.advisor_should_confirm,
                profile.remaining_risks,
            )
            blueprint.status = "decision_readiness_built"
            blueprint.log("decision_readiness_station")
            return blueprint

        missing = set(
            blueprint.knowledge_gap.missing_concepts
            if blueprint.knowledge_gap
            else []
        )

        customer_can = [
            "Explain Copay in claim-stage terms.",
            "Identify out-of-pocket risk before buying.",
            "Compare premium saving against future cash liability.",
        ]
        advisor_should_confirm = [
            "Customer knows Copay may still apply even when sum insured is sufficient.",
            "Customer knows Copay does not remove non-admissible expenses.",
        ]
        risks = ["Customer may still forget the concept under hospital stress."]

        if "admissible_claim" in missing:
            customer_can.append(
                "Calculate Copay on the admissible claim amount, not the hospital bill."
            )
            advisor_should_confirm.append(
                "Customer can calculate approved amount based Copay in a mock bill."
            )

        if "treatment_zone" in missing:
            customer_can.append(
                "Decide whether zone-based premium saving is worth treatment-city risk."
            )
            advisor_should_confirm.append(
                "Customer has named likely treatment city for major illness."
            )

        blueprint.decision_readiness = DecisionReadiness(
            customer_can,
            advisor_should_confirm,
            risks,
        )
        blueprint.status = "decision_readiness_built"
        blueprint.log("decision_readiness_station")
        return blueprint