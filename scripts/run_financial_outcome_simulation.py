from __future__ import annotations

import json
from pathlib import Path

from knowledge_domains.health.financial_outcome import FinancialOutcomeSimulationCell


def main() -> None:
    cell = FinancialOutcomeSimulationCell()
    outputs = cell.run(hospital_bill=500000, non_medical_expenses=50000, copay_percent=0.10)
    asset = json.loads(Path(outputs["asset"]).read_text(encoding="utf-8"))
    fin = asset["financial_outcome"]
    claim = asset["claim_processing"]
    policy = asset["policy_conditions"]

    print("=" * 70)
    print("FINANCIAL OUTCOME SIMULATION CELL")
    print("=" * 70)
    print(f"Hospital Bill         : ₹{asset['scenario']['hospital_bill']:,.0f}")
    print(f"Non Medical Expenses  : ₹{claim['non_medical_deductions']:,.0f}")
    print(f"Admissible Claim      : ₹{claim['admissible_claim']:,.0f}")
    print(f"Copay ({policy['copay_percent']:.0%})          : ₹{policy['copay_amount']:,.0f}")
    print(f"Insurance Pays        : ₹{fin['insurer_pays']:,.0f}")
    print(f"Customer Pays         : ₹{fin['customer_pays']:,.0f}")
    print(f"Customer Share        : {fin['effective_customer_share_percent']:.0f}%")
    print(f"Shock Level           : {fin['financial_shock_level']}")
    print(f"Certification         : {asset['certification_status']}")
    print("-" * 70)
    print(f"Asset                 : {outputs['asset']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
