from __future__ import annotations

from ..concept_profiles import get_concept_profile
from ..mental_model_models import KnowledgeGap
from ..transformation_blueprint import TransformationBlueprint


class KnowledgeGapStation:
    """Identifies missing concepts and broken connections between current and target models."""

    def manufacture(self, blueprint: TransformationBlueprint) -> TransformationBlueprint:
        profile = get_concept_profile(blueprint.concept_id)

        if profile:
            blueprint.knowledge_gap = KnowledgeGap(
                missing_concepts=sorted(set(profile.missing_concepts)),
                incorrect_assumptions=sorted(set(profile.incorrect_assumptions)),
                incorrect_connections=sorted(set(profile.incorrect_connections)),
                severity=profile.severity,
            )
            blueprint.status = "knowledge_gap_analyzed"
            blueprint.log("knowledge_gap_station")
            return blueprint

        text = (blueprint.source_report.get("observation", {}).get("observation") or "").lower()
        linked = blueprint.source_report.get("relationships", [])

        missing = []
        incorrect_assumptions = []
        incorrect_connections = []

        if blueprint.concept_id == "copay":
            if "admissible_claim" in linked or "admissible" in text or "approved" in text:
                missing.append("admissible_claim")
                incorrect_connections.append("hospital_bill -> copay")
                incorrect_assumptions.append(
                    "Copay is calculated before deductions and policy conditions."
                )

            if "zone" in text or "zone_copay" in linked:
                missing.append("treatment_zone")
                incorrect_assumptions.append(
                    "Treatment city does not change claim-stage liability."
                )

            if "non_medical_expenses" in linked or "non-medical" in text:
                missing.append("non_medical_expenses")

        if not missing:
            missing = ["concept_context"]
            incorrect_assumptions = ["Customer model is incomplete or context-free."]

        severity = (
            "high"
            if any(x in missing for x in ["admissible_claim", "treatment_zone"])
            else "medium"
        )

        blueprint.knowledge_gap = KnowledgeGap(
            missing_concepts=sorted(set(missing)),
            incorrect_assumptions=sorted(set(incorrect_assumptions)),
            incorrect_connections=sorted(set(incorrect_connections)),
            severity=severity,
        )
        blueprint.status = "knowledge_gap_analyzed"
        blueprint.log("knowledge_gap_station")
        return blueprint