from __future__ import annotations

from .financial_outcome_models import ClaimAdjudication, PolicyAdjustment, Scenario


class FSRSRuleEngine:
    COPAY_RULE_ID = "FSRS-CP-001"

    def apply_standard_copay(self, scenario: Scenario, claim: ClaimAdjudication) -> PolicyAdjustment:
        amount = claim.admissible_claim * scenario.copay_percent
        return PolicyAdjustment(
            rule_id=self.COPAY_RULE_ID,
            adjustment_type="standard_copay",
            base_amount=claim.admissible_claim,
            percentage=scenario.copay_percent,
            adjustment_amount=amount,
            reason="Standard copay is calculated on admissible claim amount, not gross hospital bill.",
        )
