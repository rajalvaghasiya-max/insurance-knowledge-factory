from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .financial_outcome_models import (
    Certification,
    ClaimAdjudication,
    FinancialOutcome,
    FinancialOutcomeAsset,
    PolicyAdjustment,
    Scenario,
    ShockAnalysis,
    stable_id,
    utc_now,
)


class FinancialOutcomeAssetBuilder:
    def build(
        self,
        scenario: Scenario,
        claim: ClaimAdjudication,
        copay: PolicyAdjustment,
        outcome: FinancialOutcome,
        shock: ShockAnalysis,
        certification: Certification,
        source_assets: Dict[str, Any] | None = None,
    ) -> FinancialOutcomeAsset:
        asset_id = stable_id("foa", f"{scenario.scenario_id}|{claim.admissible_claim}|{copay.adjustment_amount}")
        return FinancialOutcomeAsset(
            asset_id=asset_id,
            concept_id=scenario.concept_id,
            concept_name=scenario.concept_name,
            version="1.0",
            certification_status=certification.status,
            source_assets=source_assets or {},
            scenario=asdict(scenario),
            claim_processing={
                "gross_bill": claim.hospital_bill,
                "non_medical_deductions": claim.non_medical_expenses,
                "admissible_claim": claim.admissible_claim,
                "rules_applied": [claim.rule_id],
                "explanation": claim.explanation,
            },
            policy_conditions={
                "copay_percent": copay.percentage,
                "copay_amount": round(copay.adjustment_amount, 2),
                "rules_applied": [copay.rule_id],
                "reason": copay.reason,
            },
            financial_outcome={
                "insurer_pays": outcome.insurer_pays,
                "customer_pays": outcome.customer_pays,
                "out_of_pocket_breakdown": outcome.out_of_pocket_breakdown,
                "effective_customer_share_percent": outcome.customer_share_percent,
                "financial_shock_level": shock.shock_level,
                "shock_rules_applied": shock.rule_ids,
            },
            explanation={
                "plain_language_summary": f"From a hospital bill of ₹{scenario.hospital_bill:,.0f}, the insurer pays ₹{outcome.insurer_pays:,.0f} and the customer pays ₹{outcome.customer_pays:,.0f}.",
                "why_customer_pays": [
                    f"₹{scenario.non_medical_expenses:,.0f} is paid by the customer because it is treated as non-medical expense in this scenario.",
                    f"₹{copay.adjustment_amount:,.0f} is paid by the customer because {scenario.copay_percent:.0%} copay applies on admissible claim of ₹{claim.admissible_claim:,.0f}.",
                ],
                "golden_rule": "Never calculate Copay on the hospital bill; calculate it on the admissible claim amount.",
                "common_wrong_expectation": f"Customer may expect to pay ₹{scenario.hospital_bill * scenario.copay_percent:,.0f}, but that ignores non-medical deductions and admissible claim sequencing.",
            },
            decision_readiness={
                "customer_can": [
                    "Estimate out-of-pocket liability before claim settlement.",
                    "Separate non-medical deductions from copay share.",
                    "Calculate copay on admissible claim amount.",
                ],
                "advisor_should_confirm": [
                    "Customer knows non-medical expenses are paid separately.",
                    "Customer knows copay applies after admissible claim is calculated.",
                ],
                "warning_flags": ["Financial shock level is HIGH"] if shock.shock_level in {"HIGH", "CRITICAL"} else [],
            },
            verification={
                "question": "If the hospital bill is ₹5,00,000, non-medical expenses are ₹50,000 and copay is 10%, how much does the customer pay?",
                "correct_answer": "₹95,000",
                "common_wrong_answer": "₹50,000",
                "why_wrong": "The wrong answer calculates 10% on the hospital bill and ignores non-medical expenses and admissible claim sequencing.",
            },
            certification=asdict(certification),
            factory_signature={
                "factory": "PolicyScna Knowledge Factory",
                "production_cell": "FinancialOutcomeSimulationCell",
                "version": "1.0",
                "deterministic": True,
                "created_at": utc_now(),
            },
        )
