from capability_control.catalog import load_catalog
from capability_control.preflight import preflight_capability


def _catalog():
    return load_catalog()


def test_preflight_surfaces_existing_intent_context_capabilities():
    result = preflight_capability(
        catalog=_catalog(),
        query="intent domain entity scope customer context clarify planning",
        limit=10,
    )
    ids = {candidate.capability_id for candidate in result.candidates}
    assert "II.INTENT.DETERMINISTIC_ANALYZER" in ids
    assert "II.CONTEXT.BUILDER" in ids
    assert result.new_authorized is False


def test_preflight_surfaces_existing_planning_evidence_capabilities():
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
        # Keep enough headroom for legitimate catalog growth while preserving the
        # semantic assertion that the established generic execution runtime remains
        # discoverable alongside decision and explanation capabilities.
        limit=16,
    )
    ids = {candidate.capability_id for candidate in result.candidates}
    assert "II.DECISION.DETERMINISTIC_SAFETY_GATE" in ids
    assert "II.EXPLANATION.EVIDENCE_LOCKED_GENERATOR" in ids
    assert "II.ORCHESTRATION.EXECUTION_RUNTIME" in ids
    assert result.new_authorized is False
