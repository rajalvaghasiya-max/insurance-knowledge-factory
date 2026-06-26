from __future__ import annotations

from .financial_outcome_models import FinancialOutcome, ShockAnalysis, Scenario


class ShockAnalyzer:
    PERCENT_RULE_ID = "FSRS-FS-001"
    CLASSIFICATION_RULE_ID = "FSRS-FS-002"

    def classify(self, shock_percent: float) -> str:
        if shock_percent < 5:
            return "LOW"
        if shock_percent < 15:
            return "MEDIUM"
        if shock_percent < 30:
            return "HIGH"
        return "CRITICAL"

    def analyze(self, scenario: Scenario, outcome: FinancialOutcome) -> ShockAnalysis:
        shock_percent = (outcome.customer_pays / scenario.hospital_bill) * 100
        level = self.classify(shock_percent)
        return ShockAnalysis(
            rule_ids=[self.PERCENT_RULE_ID, self.CLASSIFICATION_RULE_ID],
            shock_percent=round(shock_percent, 2),
            shock_level=level,
            explanation=f"Customer pays {round(shock_percent, 2)}% of the hospital bill; classified as {level} by FSRS-FS-002.",
        )
