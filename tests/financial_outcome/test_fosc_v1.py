from pathlib import Path
import json

from knowledge_domains.health.financial_outcome.scenario_builder import ScenarioBuilder
from knowledge_domains.health.financial_outcome.claim_adjudication_station import ClaimAdjudicationStation
from knowledge_domains.health.financial_outcome.fsrs_rule_engine import FSRSRuleEngine
from knowledge_domains.health.financial_outcome.outcome_builder import OutcomeBuilder
from knowledge_domains.health.financial_outcome.shock_analyzer import ShockAnalyzer
from knowledge_domains.health.financial_outcome.quality_engine import FinancialOutcomeQualityEngine
from knowledge_domains.health.financial_outcome import FinancialOutcomeSimulationCell


def test_scenario_builder_validation_and_defaults():
    s = ScenarioBuilder().build(500000, 50000, 0.10)
    assert s.concept_id == "copay"
    assert s.hospital_bill == 500000
    assert s.non_medical_expenses == 50000
    assert s.copay_percent == 0.10


def test_claim_adjudication_uses_fsrs_ac_001():
    s = ScenarioBuilder().build(500000, 50000, 0.10)
    claim = ClaimAdjudicationStation().run(s)
    assert claim.rule_id == "FSRS-AC-001"
    assert claim.admissible_claim == 450000


def test_standard_copay_uses_admissible_claim():
    s = ScenarioBuilder().build(500000, 50000, 0.10)
    claim = ClaimAdjudicationStation().run(s)
    copay = FSRSRuleEngine().apply_standard_copay(s, claim)
    assert copay.rule_id == "FSRS-CP-001"
    assert copay.adjustment_amount == 45000


def test_outcome_and_shock_are_correct():
    s = ScenarioBuilder().build(500000, 50000, 0.10)
    claim = ClaimAdjudicationStation().run(s)
    copay = FSRSRuleEngine().apply_standard_copay(s, claim)
    outcome = OutcomeBuilder().build(s, claim, copay)
    shock = ShockAnalyzer().analyze(s, outcome)
    assert outcome.insurer_pays == 405000
    assert outcome.customer_pays == 95000
    assert outcome.customer_share_percent == 19
    assert shock.shock_level == "HIGH"


def test_quality_requires_arithmetic_and_rule_traceability():
    s = ScenarioBuilder().build(500000, 50000, 0.10)
    claim = ClaimAdjudicationStation().run(s)
    copay = FSRSRuleEngine().apply_standard_copay(s, claim)
    outcome = OutcomeBuilder().build(s, claim, copay)
    shock = ShockAnalyzer().analyze(s, outcome)
    quality = FinancialOutcomeQualityEngine().inspect(s, claim, copay, outcome, shock)
    assert quality.pass_ is True
    assert quality.checks["arithmetic_reconciles"] is True
    assert quality.checks["rule_traceability_present"] is True


def test_fosc_pipeline_writes_certified_asset(tmp_path: Path):
    outputs = FinancialOutcomeSimulationCell(output_dir=tmp_path).run(500000, 50000, 0.10)
    asset = json.loads(Path(outputs["asset"]).read_text(encoding="utf-8"))
    assert asset["certification_status"] == "PASS"
    assert asset["claim_processing"]["admissible_claim"] == 450000
    assert asset["policy_conditions"]["copay_amount"] == 45000
    assert asset["financial_outcome"]["insurer_pays"] == 405000
    assert asset["financial_outcome"]["customer_pays"] == 95000
    assert asset["financial_outcome"]["financial_shock_level"] == "HIGH"
