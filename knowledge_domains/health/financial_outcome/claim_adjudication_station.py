from __future__ import annotations

from .financial_outcome_models import ClaimAdjudication, Scenario


class ClaimAdjudicationStation:
    RULE_ID = "FSRS-AC-001"

    def run(self, scenario: Scenario) -> ClaimAdjudication:
        admissible = scenario.hospital_bill - scenario.non_medical_expenses
        return ClaimAdjudication(
            rule_id=self.RULE_ID,
            rule_name="Non Medical Expense Deduction",
            hospital_bill=scenario.hospital_bill,
            non_medical_expenses=scenario.non_medical_expenses,
            admissible_claim=admissible,
            explanation="Non-medical expenses are removed before claim settlement to derive admissible claim.",
        )
