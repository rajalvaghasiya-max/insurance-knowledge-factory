from __future__ import annotations

from .financial_outcome_models import ClaimAdjudication, FinancialOutcome, PolicyAdjustment, Scenario


class OutcomeBuilder:
    def build(self, scenario: Scenario, claim: ClaimAdjudication, copay: PolicyAdjustment, shock_level: str = "PENDING") -> FinancialOutcome:
        insurer_pays = claim.admissible_claim - copay.adjustment_amount
        customer_pays = scenario.non_medical_expenses + copay.adjustment_amount
        share_percent = (customer_pays / scenario.hospital_bill) * 100
        return FinancialOutcome(
            insurer_pays=round(insurer_pays, 2),
            customer_pays=round(customer_pays, 2),
            customer_share_percent=round(share_percent, 2),
            shock_level=shock_level,
            out_of_pocket_breakdown={
                "non_medical_expenses": round(scenario.non_medical_expenses, 2),
                "copay": round(copay.adjustment_amount, 2),
            },
        )
