from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_v8_initial_waiting_period_binding_spec.json"
)


def _spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_hdfc_initial_wait_uses_existing_generic_scalar_binding_contract() -> None:
    spec = _spec()
    assert spec["schema_version"] == "1.0"
    assert spec["binding_type"] == "waiting_period_binding_v1"
    assert spec["reviewed_by_human"] is True
    assert spec["manufacturing_status"] == "resolved_scalar_ready_for_binding"
    assert spec["governance"]["cold_start_runtime_python_changes"] == 0


def test_hdfc_initial_wait_binds_exact_page_32_candidate() -> None:
    spec = _spec()
    selections = spec["evidence_selections"]
    assert len(selections) == 1
    assert selections[0] == {
        "role": "mechanism",
        "document_id": "hdfc_ergo_optima_secure_policy_wording_v8",
        "candidate_id": "candidate_page_32",
        "candidate_text_sha256": "c3a9935698e24f4411d12a47bdcc1e3b22573ccca1b84adb6faa4cf647737c42",
    }


def test_hdfc_initial_wait_is_product_fixed_and_preserves_material_mechanics() -> None:
    mechanic = _spec()["mechanic"]
    assert mechanic["waiting_period_type"] == "INITIAL"
    assert mechanic["duration_value"] == 30
    assert mechanic["duration_unit"] == "DAYS"
    assert mechanic["start_basis"] == "POLICY_INCEPTION"
    assert mechanic["value_source"] == "PRODUCT_FIXED"
    assert mechanic["schedule_dependency"] is None
    assert mechanic["scope_type"] == "POLICY_WIDE"
    assert mechanic["member_waiting_basis"] == "POLICY_INCEPTION"
    assert mechanic["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    assert set(mechanic["exclusions_or_exceptions"]) == {
        "accident_claims_where_other_policy_terms_cover_the_claim",
        "insured_person_with_continuous_coverage_for_more_than_12_months",
    }
    assert "more than 12 months" in mechanic["continuity_dependency"]


def test_hdfc_initial_wait_does_not_claim_publication_or_customer_eligibility() -> None:
    governance = _spec()["governance"]
    assert governance["publication_authorized"] is False
    assert governance["policy_specific_eligibility_authorized"] is False
    assert governance["scalar_binding_authorized"] is True
    assert governance["schedule_resolution_basis"] is None
