from knowledge_domains.health.knowledge_distillation.knowledge_distillation_engine import KnowledgeDistillationEngine
from knowledge_domains.health.knowledge_distillation.observation_models import ObservationRecord


def test_misconception_creates_mental_model_opportunity():
    obs = ObservationRecord(
        observation_id="T1",
        concept_id="copay",
        title="Customer thinks Copay is on total bill",
        observation="Customer assumes copay is calculated on the hospital bill, not approved amount.",
        category="customer_reality",
        observation_type="misconception",
        source="test",
        confidence="high",
        frequency="high",
        financial_impact="high",
        emotional_impact="high",
        decision_impact="high",
    )
    report = KnowledgeDistillationEngine().distill(obs)
    asset_types = {o.asset_type for o in report.manufacturing_opportunities}
    assert "mental_model_asset" in asset_types
    assert "understanding_gap" in asset_types
    assert report.knowledge_potential.overall >= 7


def test_financial_observation_creates_simulation():
    obs = ObservationRecord(
        observation_id="T2",
        concept_id="copay",
        title="Large bill creates out-of-pocket liability",
        observation="A 5 lakh hospital bill with 20% copay creates a major cash burden.",
        category="financial_reality",
        observation_type="financial_loss",
        source="test",
        confidence="high",
        financial_impact="very high",
        emotional_impact="medium",
        decision_impact="high",
    )
    report = KnowledgeDistillationEngine().distill(obs)
    asset_types = {o.asset_type for o in report.manufacturing_opportunities}
    assert "financial_simulation" in asset_types
    assert "golden_rule" in asset_types


def test_relationship_detector_links_claim_concepts():
    obs = ObservationRecord(
        observation_id="T3",
        concept_id="copay",
        title="TPA discharge approval shock",
        observation="During cashless discharge the TPA approval applies copay after non-medical expenses are removed.",
        category="claims_reality",
        observation_type="claim_insight",
        source="test",
        confidence="high",
    )
    report = KnowledgeDistillationEngine().distill(obs)
    assert "cashless" in report.relationships
    assert "non_medical_expenses" in report.relationships
    assert "claim_settlement" in report.relationships


def test_distillation_is_stable_for_same_observation():
    obs = ObservationRecord(
        observation_id="T4",
        concept_id="copay",
        title="Stable observation",
        observation="Customer thinks copay is a small fee.",
        category="customer_reality",
        observation_type="misconception",
        source="test",
    )
    engine = KnowledgeDistillationEngine()
    a = engine.distill(obs)
    b = engine.distill(obs)
    assert a.distillation_id == b.distillation_id
