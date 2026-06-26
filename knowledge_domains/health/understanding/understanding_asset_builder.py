from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .understanding_asset_models import UnderstandingAsset, factory_signature, stable_id
from .understanding_certification_engine import UnderstandingCertificationEngine


class CopayUnderstandingAssetBuilder:
    """Builds the certified Copay Understanding Asset requested by GCP gap analysis."""

    def build_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "concept_id": "copay",
            "concept_name": "Copay",
            "version": "1.0",
            "reality": (
                "Copay is the percentage of the admissible claim amount that must be paid by the customer. "
                "The insurer first determines admissible expenses after policy conditions, exclusions, and deductions. "
                "Copay is then applied to that admissible claim amount, not to the total hospital bill."
            ),
            "common_misunderstanding": (
                "Many customers believe that a 10% Copay means 10% of the hospital bill because the hospital bill is the only number they see. "
                "They rarely see how the insurer calculates the admissible claim amount."
            ),
            "root_causes": [
                "Hospital bill is visible to the customer.",
                "Admissible claim calculation is usually invisible until claim settlement.",
                "Policy wording explains Copay percentage but often does not show claim math.",
                "Customers naturally anchor on the total hospital bill amount.",
                "Advisors may explain premium impact but not claim-stage financial impact.",
            ],
            "consequence": (
                "Customers underestimate their future out-of-pocket liability. At claim time they may feel that the insurer paid less than expected, "
                "creating confusion, dissatisfaction, and loss of trust."
            ),
            "example": {
                "hospital_bill": 500000,
                "non_medical_expenses": 50000,
                "admissible_claim": 450000,
                "copay_percent": 10,
                "copay_amount": 45000,
            },
            "expectation_gap": {
                "customer_expected_payment": 50000,
                "actual_copay": 45000,
                "actual_customer_payment": 95000,
                "gap_reason": [
                    "Customer ignored non-medical deductions.",
                    "Customer calculated Copay on hospital bill instead of admissible claim.",
                ],
            },
            "golden_rule": "Never calculate Copay on the hospital bill. Always calculate Copay on the admissible claim amount.",
            "transformation": {
                "old_understanding": "Copay means I pay 10% of the hospital bill.",
                "new_understanding": "Copay means I pay a percentage of the admissible claim amount after deductions and exclusions.",
            },
            "verification": {
                "question": "Hospital Bill = ₹5,00,000, Non-Medical Expenses = ₹50,000, Copay = 10%. How much Copay applies?",
                "expected_answer": 45000,
                "common_wrong_answer": 50000,
                "why_wrong": "The wrong answer calculates Copay on the hospital bill and ignores admissible claim sequencing.",
            },
            "source_assets": {
                "gap_source": "GCP-001 identified understanding_asset as missing for copay.",
                "related_assets": [
                    "mental_model_asset",
                    "financial_outcome_asset",
                ],
            },
        }
        payload["asset_id"] = stable_id("ua", payload)
        return payload

    def build(self) -> UnderstandingAsset:
        payload = self.build_payload()
        certification = UnderstandingCertificationEngine().certify(payload)
        return UnderstandingAsset(
            asset_id=payload["asset_id"],
            concept_id=payload["concept_id"],
            concept_name=payload["concept_name"],
            version=payload["version"],
            certification_status=certification.status,
            reality=payload["reality"],
            common_misunderstanding=payload["common_misunderstanding"],
            root_causes=payload["root_causes"],
            consequence=payload["consequence"],
            example=payload["example"],
            expectation_gap=payload["expectation_gap"],
            golden_rule=payload["golden_rule"],
            transformation=payload["transformation"],
            verification=payload["verification"],
            source_assets=payload["source_assets"],
            certification=certification.to_dict(),
            factory_signature=factory_signature(),
        )

    def write_outputs(self, repo_root: str | Path = ".") -> Dict[str, str]:
        repo_root = Path(repo_root)
        output_dir = repo_root / "knowledge" / "factory" / "golden_concepts" / "copay" / "understanding_assets"
        output_dir.mkdir(parents=True, exist_ok=True)
        asset = self.build()
        asset_path = output_dir / f"{asset.asset_id}_understanding_asset.json"
        cert_path = output_dir / f"{asset.asset_id}_understanding_certification.json"
        event_path = output_dir / f"{asset.asset_id}_understanding_event.json"
        summary_path = output_dir / "understanding_asset_summary.json"

        asset_path.write_text(json.dumps(asset.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        cert_path.write_text(json.dumps(asset.certification, ensure_ascii=False, indent=2), encoding="utf-8")
        event = {
            "event_type": "understanding_asset_manufactured",
            "asset_id": asset.asset_id,
            "concept_id": asset.concept_id,
            "status": asset.certification_status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        event_path.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {
            "production_cell": "UnderstandingAssetBuilder",
            "version": "1.0",
            "assets_manufactured": 1,
            "asset": str(asset_path),
            "certification": str(cert_path),
            "event": str(event_path),
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"asset": str(asset_path), "certification": str(cert_path), "event": str(event_path), "summary": str(summary_path)}


def build_copay_understanding_asset(repo_root: str | Path = ".") -> Dict[str, str]:
    return CopayUnderstandingAssetBuilder().write_outputs(repo_root)
