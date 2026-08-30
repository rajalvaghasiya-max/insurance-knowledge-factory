from pathlib import Path

from capability_control import load_catalog
from capability_control.preflight import preflight_capability


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "governance" / "capabilities" / "catalog.json"


def _catalog():
    return load_catalog(CATALOG)


def _by_id():
    return {item.capability_id: item for item in _catalog().capabilities}


def test_core_intelligence_engines_are_registered_active_reuse():
    records = _by_id()
    expected = {
        "II.INTENT.DETERMINISTIC_ANALYZER",
        "II.PLANNING.REASONING_PLANNER",
        "II.EVIDENCE.GOVERNED_RESOLVER",
        "II.DECISION.DETERMINISTIC_SAFETY_GATE",
        "II.EXPLANATION.EVIDENCE_LOCKED_GENERATOR",
        "II.ORCHESTRATION.EXECUTION_RUNTIME",
    }
    assert expected <= records.keys()
    for capability_id in expected:
        assert records[capability_id].lifecycle_status == "ACTIVE"
        assert records[capability_id].reuse_policy == "REUSE"


def test_underlying_engines_do_not_claim_guard_authority():
    records = _by_id()
    evidence = records["II.EVIDENCE.GOVERNED_RESOLVER"]
    decision = records["II.DECISION.DETERMINISTIC_SAFETY_GATE"]
    explanation = records["II.EXPLANATION.EVIDENCE_LOCKED_GENERATOR"]

    assert "II.EVIDENCE.INSTANCE_ENFORCEMENT" in evidence.authority_role
    assert "II.DECISION.AUTHORITY_ENFORCEMENT" in decision.authority_role
    assert "II.EXPLANATION.AUTHORITY_ENFORCEMENT" in explanation.authority_role


def test_orchestration_runtime_defers_to_canonical_order_authority():
    runtime = _by_id()["II.ORCHESTRATION.EXECUTION_RUNTIME"]
    assert "II.ORCHESTRATION.CANONICAL_GUARDED_ORDER" in runtime.authority_role
    assert "pilot/certification/hardening" in (runtime.notes or "")


def test_preflight_surfaces_existing_planning_and_evidence_capabilities():
    result = preflight_capability(
        catalog=_catalog(),
        query="plan required evidence then resolve governed source lineage sufficiency",
        limit=10,
    )
    ids = {candidate.capability_id for candidate in result.candidates}
    assert "II.PLANNING.REASONING_PLANNER" in ids
    assert "II.EVIDENCE.GOVERNED_RESOLVER" in ids
    assert result.new_authorized is False


def test_preflight_surfaces_existing_decision_explanation_orchestration_capabilities():
    result = preflight_capability(
        catalog=_catalog(),
        query="safety gate approved findings explanation adapter orchestration execution",
        limit=16,
    )
    ids = {candidate.capability_id for candidate in result.candidates}
    assert "II.DECISION.DETERMINISTIC_SAFETY_GATE" in ids
    assert "II.EXPLANATION.EVIDENCE_LOCKED_GENERATOR" in ids
    assert "II.ORCHESTRATION.EXECUTION_RUNTIME" in ids
    assert result.new_authorized is False
