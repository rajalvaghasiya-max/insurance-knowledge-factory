from __future__ import annotations

from typing import Dict, Any, List
from .package_models import AssetRecord


class DependencyValidator:
    REQUIRED = [
        "knowledge_asset",
        "understanding_asset",
        "mental_model_asset",
        "financial_outcome_asset",
        "advisor_intelligence_asset",
        "decision_intelligence_asset",
    ]
    CORE = ["mental_model_asset", "financial_outcome_asset"]

    def validate(self, inventory: Dict[str, AssetRecord]) -> Dict[str, Any]:
        missing = [a for a in self.REQUIRED if inventory.get(a, AssetRecord(a, "MISSING")).status != "FOUND"]
        core_missing = [a for a in self.CORE if inventory.get(a, AssetRecord(a, "MISSING")).status != "FOUND"]
        status = "PASS" if not missing else ("PASS_WITH_GAPS" if not core_missing else "FAIL")
        return {
            "status": status,
            "required_assets": self.REQUIRED,
            "missing_assets": missing,
            "core_missing_assets": core_missing,
        }
