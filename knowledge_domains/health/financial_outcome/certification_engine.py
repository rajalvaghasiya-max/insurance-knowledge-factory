from __future__ import annotations

from .financial_outcome_models import Certification, QualityReport, Scenario, stable_id, utc_now


class FinancialOutcomeCertificationEngine:
    def certify(self, scenario: Scenario, quality: QualityReport) -> Certification:
        cert_id = stable_id("foc", f"{scenario.scenario_id}|{quality.pass_}")
        return Certification(
            certification_id=cert_id,
            asset_id="pending_until_asset_assembly",
            concept_id=scenario.concept_id,
            status="PASS" if quality.pass_ else "FAIL",
            checks=quality.checks,
            created_at=utc_now(),
        )
