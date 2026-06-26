from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, List
from .package_models import AssetRecord, CoverageAnalysis


class GapAnalyzer:
    FUTURE_GAPS = [
        "regulatory_knowledge_family_not_yet_integrated",
        "alternative_financial_scenarios_not_yet_integrated",
        "real_claim_case_library_not_yet_integrated",
    ]

    def analyze(self, inventory: Dict[str, AssetRecord], coverage: CoverageAnalysis) -> Dict[str, Any]:
        missing_assets = [k for k, v in asdict(coverage).items() if k != "overall" and v != "PASS"]
        return {
            "missing_assets": missing_assets,
            "future_enrichment_gaps": self.FUTURE_GAPS,
            "next_best_actions": self._next_actions(missing_assets),
        }

    def _next_actions(self, missing_assets: List[str]) -> List[str]:
        actions = []
        if "advisor_intelligence_asset" in missing_assets:
            actions.append("Build Advisor Intelligence Cell or add certified AIA for this concept.")
        if "decision_intelligence_asset" in missing_assets:
            actions.append("Build Decision Intelligence Cell or add certified DIA for this concept.")
        if "knowledge_asset" in missing_assets or "understanding_asset" in missing_assets:
            actions.append("Backfill certified Department IV/V assets for this concept.")
        if not actions:
            actions.append("Run cross-concept GMVS with the next concept.")
        return actions
