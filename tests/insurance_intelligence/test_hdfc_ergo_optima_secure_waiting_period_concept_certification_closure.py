import json
from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE


CLOSURE_PATH = Path(
    "docs/architecture/"
    "hdfc_ergo_optima_secure_v8_waiting_period_concept_certification_closure_2026-08-22.json"
)


def _closure() -> dict:
    return json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))


def test_hdfc_waiting_period_concept_closes_three_base_policy_families() -> None:
    closure = _closure()
    assert closure["concept_id"] == "waiting_period"
    assert closure["concept_status"] == "CERTIFIED"
    assert closure["certified_scope"] == "BASE_POLICY_WORDING"

    families = {item["waiting_period_type"]: item for item in closure["certified_families"]}
    assert set(families) == {
        "INITIAL",
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
    }
    assert all(item["certification_outcome"] == "PASS" for item in families.values())
    assert all(item["completeness"] == "COMPLETE" for item in families.values())
    assert all(item["explanation_permitted"] is True for item in families.values())
    assert families["SPECIFIC_DISEASE_PROCEDURE"]["material_rules_certification_outcome"] == "PASS"
    assert families["SPECIFIC_DISEASE_PROCEDURE"]["material_rules_completeness"] == "COMPLETE"


def test_hdfc_ped_concept_certification_preserves_unresolved_schedule_selection() -> None:
    closure = _closure()
    ped = next(item for item in closure["certified_families"] if item["waiting_period_type"] == "PRE_EXISTING_DISEASE")
    assert ped["authoritative_options"] == ["12 MONTHS", "24 MONTHS", "36 MONTHS"]
    assert ped["policy_instance_selected_duration"] == "UNRESOLVED_WITHOUT_POLICY_SCHEDULE"

    boundary = closure["governance_boundary"]
    assert boundary["customer_specific_schedule_resolution_is_not_implied"] is True
    assert boundary["ped_selected_duration_requires_policy_schedule"] is True
    assert boundary["publication_authorized"] is False
    assert boundary["comparison_ready"] is False
    assert boundary["decision_support_ready"] is False
    assert boundary["claim_payment_prediction_authorized"] is False


def test_hdfc_concept_certification_is_explicitly_base_policy_scoped() -> None:
    closure = _closure()
    scope = closure["scope_boundary"]
    assert scope["base_policy_waiting_period_families_certified"] is True
    assert scope["separate_add_on_waiting_periods_included"] is False
    assert scope["parenthood_add_on_waiting_period_not_certified_by_this_closure"] is True
    assert scope["underwriting_specific_waiting_periods_not_resolved_as_product_level_defaults"] is True
    assert closure["governance_boundary"]["add_on_waiting_period_inference_authorized"] is False


def test_hdfc_waiting_period_enters_registry_as_certified_without_downstream_readiness() -> None:
    waiting = next(item for item in HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE.concepts if item.concept_id == "waiting_period")
    assert waiting.status is ConceptCoverageStatus.CERTIFIED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    assert HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE.comparison_ready_concept_ids == ()
    assert HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE.decision_support_ready_concept_ids == ()
    assert "docs/architecture/hdfc_ergo_optima_secure_v8_waiting_period_concept_certification_closure_2026-08-22.json" in waiting.evidence_reference_ids
    lowered = tuple(item.lower() for item in waiting.limitations)
    assert any("base-policy" in item for item in lowered)
    assert any("parenthood" in item and "not certified" in item for item in lowered)
