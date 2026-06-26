from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Dict

from .claim_adjudication_station import ClaimAdjudicationStation
from .certification_engine import FinancialOutcomeCertificationEngine
from .financial_outcome_asset_builder import FinancialOutcomeAssetBuilder
from .fsrs_rule_engine import FSRSRuleEngine
from .outcome_builder import OutcomeBuilder
from .quality_engine import FinancialOutcomeQualityEngine
from .scenario_builder import ScenarioBuilder
from .shock_analyzer import ShockAnalyzer
from .financial_outcome_models import FinancialOutcomeAsset, utc_now


class FinancialOutcomeSimulationCell:
    def __init__(self, output_dir: str | Path = "knowledge/factory/financial_outcomes/copay") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scenario_builder = ScenarioBuilder()
        self.claim_station = ClaimAdjudicationStation()
        self.rule_engine = FSRSRuleEngine()
        self.outcome_builder = OutcomeBuilder()
        self.shock_analyzer = ShockAnalyzer()
        self.quality_engine = FinancialOutcomeQualityEngine()
        self.certification_engine = FinancialOutcomeCertificationEngine()
        self.asset_builder = FinancialOutcomeAssetBuilder()

    def run(
        self,
        hospital_bill: float = 500000,
        non_medical_expenses: float = 50000,
        copay_percent: float = 0.10,
        source_assets: Dict[str, Any] | None = None,
    ) -> Dict[str, str]:
        scenario = self.scenario_builder.build(hospital_bill, non_medical_expenses, copay_percent)
        claim = self.claim_station.run(scenario)
        copay = self.rule_engine.apply_standard_copay(scenario, claim)
        preliminary_outcome = self.outcome_builder.build(scenario, claim, copay)
        shock = self.shock_analyzer.analyze(scenario, preliminary_outcome)
        outcome = self.outcome_builder.build(scenario, claim, copay, shock.shock_level)
        quality = self.quality_engine.inspect(scenario, claim, copay, outcome, shock)
        certification = self.certification_engine.certify(scenario, quality)
        asset = self.asset_builder.build(scenario, claim, copay, outcome, shock, certification, source_assets)
        certification = replace(certification, asset_id=asset.asset_id)
        asset = self.asset_builder.build(scenario, claim, copay, outcome, shock, certification, source_assets)
        return self._write_outputs(asset, quality, certification)

    def _write_outputs(self, asset: FinancialOutcomeAsset, quality, certification) -> Dict[str, str]:
        asset_path = self.output_dir / f"{asset.asset_id}_financial_outcome_asset.json"
        quality_path = self.output_dir / f"{asset.asset_id}_quality_report.json"
        certification_path = self.output_dir / f"{asset.asset_id}_certification.json"
        event_path = self.output_dir / f"{asset.asset_id}_event.json"
        summary_path = self.output_dir / "financial_outcome_summary.json"

        asset_path.write_text(json.dumps(asset.to_dict(), indent=2), encoding="utf-8")
        quality_path.write_text(json.dumps(quality.to_dict(), indent=2), encoding="utf-8")
        certification_path.write_text(json.dumps(asdict(certification), indent=2), encoding="utf-8")
        event = {
            "event_type": "financial_outcome_asset_manufactured",
            "asset_id": asset.asset_id,
            "concept_id": asset.concept_id,
            "status": certification.status,
            "created_at": utc_now(),
        }
        event_path.write_text(json.dumps(event, indent=2), encoding="utf-8")
        summary = {
            "production_cell": "Financial Outcome Simulation Cell",
            "version": "1.0",
            "assets_manufactured": 1,
            "outputs": {
                "asset": str(asset_path),
                "quality": str(quality_path),
                "certification": str(certification_path),
                "event": str(event_path),
            },
            "financial_outcome": asset.financial_outcome,
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary["outputs"]
