from __future__ import annotations

from pathlib import Path

from factory_core.canonical.waiting_period_binding import WaitingPeriodBinding
from insurance_intelligence.rule_certification.waiting_period import (
    build_waiting_period_certification_case,
    run_waiting_period_certification_case,
)
from insurance_intelligence.rule_certification.waiting_period_material_rules import (
    build_waiting_period_material_rules_certification_case,
    run_waiting_period_material_rules_certification_case,
)


ROOT = Path(__file__).resolve().parents[2]
BASE_SPEC = "docs/architecture/star_health_star_comprehensive_ped_waiting_period_binding_spec.json"
RULES_SPEC = "docs/architecture/star_health_star_comprehensive_ped_material_rules_spec.json"


def test_star_ped_scalar_binding_preserves_current_primary_legal_mechanics() -> None:
    result = WaitingPeriodBinding().bind_from_spec_file(
        spec_path=ROOT / BASE_SPEC,
        repository_root=ROOT,
        bound_at="2026-08-22T00:00:00+00:00",
    )
    manifest = result.manifest
    mechanic = manifest["mechanic"]

    assert manifest["binding_status"] == "reviewed_waiting_period_bound_not_published"
    assert manifest["publication_status"] == "bound_not_published"
    assert mechanic["waiting_period_type"] == "PRE_EXISTING_DISEASE"
    assert mechanic["duration_value"] == 36
    assert mechanic["duration_unit"] == "MONTHS"
    assert mechanic["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert mechanic["value_source"] == "PRODUCT_FIXED"
    assert mechanic["scope_type"] == "POLICY_WIDE"
    assert mechanic["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    assert "prior coverage" in mechanic["continuity_dependency"]
    assert manifest["evidence"] == [
        {
            "role": "mechanism",
            "document_id": "star_health_star_comprehensive_policy_wording_v1",
            "candidate_id": "candidate_page_31",
            "candidate_text_sha256": "b9f28db495943d84bbf6a900df47b18717c6300bf510f88786914ae28be11e77",
            "source_page": 31,
            "source_char_range": {"start": 80038, "end": 82942},
        }
    ]


def test_star_ped_scalar_certification_passes_complete() -> None:
    case = build_waiting_period_certification_case(
        binding_spec_path=BASE_SPEC,
        repository_root=ROOT,
    )
    result = run_waiting_period_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    checks = {item.component_id: item for item in result.component_checks}
    assert checks["waiting_period_duration"].passed is True
    assert checks["waiting_period_subject"].passed is True
    assert checks["start_basis"].passed is True
    assert checks["applicability_scope"].passed is True
    assert checks["continuity_or_credit_rule"].passed is True


def test_star_ped_post_wait_condition_is_certified_separately() -> None:
    case = build_waiting_period_material_rules_certification_case(
        binding_spec_path=RULES_SPEC,
        repository_root=ROOT,
    )
    result = run_waiting_period_material_rules_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    checks = {item.component_id: item for item in result.component_checks}
    assert checks["post_wait_condition"].passed is True

    package, = case.evidence_output.evidence_packages
    assert package.field_or_topic == "POST_WAIT_CONDITION"
    assert package.page == 31
    assert package.retrieval_basis == (
        "reviewed_waiting_period_material_rules_binding",
        "ped_declared_and_accepted_after_wait",
        "candidate_page_31",
    )
    assert "declared at application" in package.claim
    assert "accepted by the insurer" in package.claim


def test_star_ped_slice_does_not_certify_optional_buy_back_cover() -> None:
    import json

    base = json.loads((ROOT / BASE_SPEC).read_text(encoding="utf-8"))
    rules = json.loads((ROOT / RULES_SPEC).read_text(encoding="utf-8"))

    assert base["governance"]["optional_buy_back_cover_included"] is False
    assert base["governance"]["optional_buy_back_cover_requires_separate_governed_certification"] is True
    assert rules["governance"]["optional_buy_back_cover_included"] is False
    assert base["governance"]["publication_authorized"] is False
    assert rules["governance"]["publication_authorized"] is False
