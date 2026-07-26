from __future__ import annotations

from ..concept_profiles import get_concept_profile
from ..mental_model_models import Verification
from ..transformation_blueprint import TransformationBlueprint


class VerificationStation:
    """Builds a scenario that verifies the transformed mental model."""

    def manufacture(self, blueprint: TransformationBlueprint) -> TransformationBlueprint:
        profile = get_concept_profile(blueprint.concept_id)

        if profile:
            blueprint.verification = Verification(
                profile.verification_scenario,
                profile.verification_question,
                profile.verification_correct_answer,
                profile.verification_common_wrong_answer,
                profile.verification_why_wrong,
                0.85,
            )
            blueprint.status = "verification_built"
            blueprint.log("verification_station")
            return blueprint

        missing = set(
            blueprint.knowledge_gap.missing_concepts
            if blueprint.knowledge_gap
            else []
        )

        if "admissible_claim" in missing:
            scenario = {
                "hospital_bill": 500000,
                "admissible_claim": 420000,
                "copay_percent": 10,
            }
            question = "How much Copay will the customer pay?"
            answer = "₹42,000"
            wrong = "₹50,000"
            why = (
                "The wrong answer calculates Copay on total hospital bill instead "
                "of admissible claim amount."
            )

        elif "treatment_zone" in missing:
            scenario = {
                "home_zone": "Zone C",
                "treatment_city": "Mumbai",
                "hospital_bill": 800000,
                "zone_copay_percent": 20,
            }
            question = "What cash liability can arise due to Zone Copay?"
            answer = "₹1,60,000 before considering other deductions."
            wrong = "No extra liability because policy sum insured is sufficient."
            why = "Zone Copay can apply because treatment is taken in a higher-cost zone."

        else:
            scenario = {"concept": blueprint.concept_id}
            question = "What question should be asked before deciding?"
            answer = "Ask about the claim-stage consequence."
            wrong = "Choose only by premium."
            why = "Premium alone does not reveal claim-stage liability."

        blueprint.verification = Verification(
            scenario,
            question,
            answer,
            wrong,
            why,
            0.85,
        )
        blueprint.status = "verification_built"
        blueprint.log("verification_station")
        return blueprint