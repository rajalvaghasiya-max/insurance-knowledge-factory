from __future__ import annotations

from .financial_outcome_models import ClaimAdjudication, FinancialOutcome, PolicyAdjustment, QualityReport, Scenario, ShockAnalysis


class FinancialOutcomeQualityEngine:
    REQUIRED_RULES = {"FSRS-AC-001", "FSRS-CP-001", "FSRS-FS-001", "FSRS-FS-002"}

    def inspect(self, scenario: Scenario, claim: ClaimAdjudication, copay: PolicyAdjustment, outcome: FinancialOutcome, shock: ShockAnalysis) -> QualityReport:
        arithmetic_ok = round(outcome.insurer_pays + outcome.customer_pays, 2) == round(scenario.hospital_bill, 2)
        rules = {claim.rule_id, copay.rule_id, *shock.rule_ids}
        traceability_ok = self.REQUIRED_RULES.issubset(rules)
        explainability_ok = bool(claim.explanation and copay.reason and shock.explanation)
        non_negative_ok = all(v >= 0 for v in [claim.admissible_claim, copay.adjustment_amount, outcome.insurer_pays, outcome.customer_pays])
        checks = {
            "arithmetic_reconciles": arithmetic_ok,
            "rule_traceability_present": traceability_ok,
            "explainability_present": explainability_ok,
            "non_negative_amounts": non_negative_ok,
        }
        return QualityReport(checks=checks, pass_=all(checks.values()))
