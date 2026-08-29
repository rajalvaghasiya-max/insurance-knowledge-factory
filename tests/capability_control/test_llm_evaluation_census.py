from __future__ import annotations

from capability_control.catalog import load_catalog
from capability_control.preflight import preflight_capability


def test_llm_evaluation_capabilities_are_registered_with_governed_lifecycle():
    catalog = load_catalog("governance/capabilities/catalog.json")
    by_id = catalog.by_id

    assert by_id["LLM.EVALUATION.CONTROLLED_PROVIDER_HARNESS"].lifecycle_status == "ACTIVE"
    assert by_id["LLM.EVALUATION.DETERMINISTIC_BASELINE"].lifecycle_status == "ACTIVE"
    assert by_id["LLM.EVALUATION.EXTERNAL_METRIC_ADVISORY"].lifecycle_status == "EXPERIMENTAL"
    assert by_id["LLM.EVALUATION.DISAGREEMENT_ANALYSIS"].lifecycle_status == "ACTIVE"
    assert by_id["LLM.EVALUATION.RESPONSIBILITY_DECISION_REPORTING"].lifecycle_status == "ACTIVE"
    assert by_id["LLM.EVALUATION.HYBRID_RENDERING_BASELINE"].lifecycle_status == "ACTIVE"
    assert by_id["LLM.RENDERING.CONTROLLED_HYBRID_RUNTIME"].lifecycle_status == "ACTIVE"
    assert by_id["II.EVALUATION.TERMINOLOGY_CONTROLLED_PACK"].lifecycle_status == "ACTIVE"


def test_old_mo021_pipeline_evaluator_is_not_misrepresented_as_current_end_to_end_fitness():
    catalog = load_catalog("governance/capabilities/catalog.json")
    record = catalog.by_id["II.EVALUATION.MO021_PIPELINE_BASELINE"]

    assert record.lifecycle_status == "DISCONNECTED"
    assert record.reuse_policy == "REPAIR"
    assert "current guarded canonical orchestration" in record.authority_role


def test_preflight_surfaces_existing_llm_comparison_capability():
    catalog = load_catalog("governance/capabilities/catalog.json")
    result = preflight_capability(
        catalog=catalog,
        query="compare LLM model outputs disagreement evaluation",
    )

    ids = tuple(candidate.capability_id for candidate in result.candidates)
    assert "LLM.EVALUATION.DISAGREEMENT_ANALYSIS" in ids
    assert "LLM.EVALUATION.HYBRID_RENDERING_BASELINE" in ids
    assert result.new_authorized is False


def test_preflight_surfaces_existing_controlled_llm_renderer():
    catalog = load_catalog("governance/capabilities/catalog.json")
    result = preflight_capability(
        catalog=catalog,
        query="build controlled LLM renderer provider fallback fidelity",
    )

    ids = tuple(candidate.capability_id for candidate in result.candidates)
    assert "LLM.RENDERING.CONTROLLED_HYBRID_RUNTIME" in ids
    assert result.new_authorized is False
