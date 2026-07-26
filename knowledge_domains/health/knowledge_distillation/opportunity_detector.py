from __future__ import annotations

from typing import List

from .distillation_models import ManufacturingOpportunity
from .observation_models import ObservationRecord


class OpportunityDetector:
    """Maps observation signals to manufacturing opportunities."""

    def detect(self, observation: ObservationRecord, signals: List[str]) -> List[ManufacturingOpportunity]:
        text = f"{observation.title} {observation.observation}".lower()
        opportunities: List[ManufacturingOpportunity] = []

        def add(asset_type: str, reason: str, priority: str, target: str) -> None:
            if asset_type not in {o.asset_type for o in opportunities}:
                opportunities.append(ManufacturingOpportunity(asset_type, reason, priority, target))

        if "misconception" in signals or any(k in text for k in ["assume", "believe", "think", "misunderstand", "fallacy", "myth"]):
            add("mental_model_asset", "Observation reveals an incorrect customer mental model.", "high", "MMTS")
            add("understanding_gap", "Incorrect belief must be compared with actual reality.", "high", "Department V")
            add("verification_question", "Misconception needs a scenario to verify transformation.", "medium", "Department V")

        if "financial" in signals or any(k in text for k in ["bill", "premium", "cash", "out-of-pocket", "lakh", "amount"]):
            add("financial_simulation", "Observation contains financial consequence or calculation potential.", "high", "Department V")
            add("golden_rule", "Financial risk should be compressed into a memorable rule.", "medium", "Department V")

        if "claim" in signals:
            add("claims_intelligence", "Observation describes claim-stage reality.", "high", "Claims Intelligence")
            add("decision_case", "Claim surprise can become a decision intelligence case.", "medium", "Decision Intelligence")

        if "advisor" in signals or "script" in text:
            add("advisor_intelligence_asset", "Observation contains advisor behaviour or explanation strategy.", "high", "Advisor Intelligence")
            add("conversation_blueprint", "Advisor explanation can be converted into reusable conversation flow.", "medium", "Advisor Intelligence")

        if "teaching" in signals or any(k in text for k in ["analogy", "example", "script", "golden rule"]):
            add("teaching_primitive", "Observation contains reusable teaching material.", "high", "Department V")

        if "decision" in signals or any(k in text for k in ["choose", "buy", "select", "trade-off"]):
            add("behaviour_goal", "Observation implies desired change in customer decision behaviour.", "medium", "MMTS")
            add("decision_intelligence_case", "Observation can help future decision readiness.", "high", "Decision Intelligence")

        if not opportunities:
            add("observation_archive", "Observation should be preserved for future review.", "low", "Observation Register")

        return opportunities
