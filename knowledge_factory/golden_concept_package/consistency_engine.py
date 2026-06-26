from __future__ import annotations

from typing import Dict, Any
from .package_models import AssetRecord


class ConsistencyEngine:
    def check(self, inventory: Dict[str, AssetRecord]) -> Dict[str, Any]:
        checks = {}
        checks["mental_model_financial_outcome"] = self._mental_model_financial(inventory)
        checks["advisor_decision_chain"] = self._presence_pair(inventory, "advisor_intelligence_asset", "decision_intelligence_asset")
        checks["knowledge_understanding_chain"] = self._presence_pair(inventory, "knowledge_asset", "understanding_asset")
        issues = [name for name, result in checks.items() if result["status"] == "FAIL"]
        warnings = [name for name, result in checks.items() if result["status"] == "WARN"]
        return {
            "status": "PASS" if not issues else "FAIL",
            "score": max(0, 100 - len(issues) * 30 - len(warnings) * 10),
            "checks": checks,
            "issues": issues,
            "warnings": warnings,
        }

    def _presence_pair(self, inventory: Dict[str, AssetRecord], a: str, b: str) -> Dict[str, Any]:
        a_found = inventory.get(a) and inventory[a].status == "FOUND"
        b_found = inventory.get(b) and inventory[b].status == "FOUND"
        if a_found and b_found:
            return {"status": "PASS", "detail": f"{a} and {b} present"}
        return {"status": "WARN", "detail": f"{a}/{b} pair incomplete"}

    def _mental_model_financial(self, inventory: Dict[str, AssetRecord]) -> Dict[str, Any]:
        mma = inventory.get("mental_model_asset")
        foa = inventory.get("financial_outcome_asset")
        if not mma or mma.status != "FOUND" or not foa or foa.status != "FOUND":
            return {"status": "WARN", "detail": "MMA or FOA missing"}
        target = str(mma.summary.get("target_model") or "").lower()
        outcome = foa.summary
        customer_pays = outcome.get("customer_pays")
        if "admissible" in target and customer_pays is not None:
            return {"status": "PASS", "detail": "FOA supports MMA transformed model with financial outcome"}
        return {"status": "WARN", "detail": "MMA/FOA link weak; needs human review"}
