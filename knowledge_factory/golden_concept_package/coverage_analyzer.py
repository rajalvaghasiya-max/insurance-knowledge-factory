from __future__ import annotations

from typing import Dict
from .package_models import AssetRecord, CoverageAnalysis


class CoverageAnalyzer:
    def analyze(self, inventory: Dict[str, AssetRecord]) -> CoverageAnalysis:
        values = {k: ("PASS" if v.status == "FOUND" else "MISSING") for k, v in inventory.items()}
        found = sum(1 for v in values.values() if v == "PASS")
        total = len(values) or 1
        overall = "COMPLETE" if found == total else ("PARTIAL" if found else "EMPTY")
        return CoverageAnalysis(
            knowledge_asset=values.get("knowledge_asset", "MISSING"),
            understanding_asset=values.get("understanding_asset", "MISSING"),
            mental_model_asset=values.get("mental_model_asset", "MISSING"),
            financial_outcome_asset=values.get("financial_outcome_asset", "MISSING"),
            advisor_intelligence_asset=values.get("advisor_intelligence_asset", "MISSING"),
            decision_intelligence_asset=values.get("decision_intelligence_asset", "MISSING"),
            overall=overall,
        )
