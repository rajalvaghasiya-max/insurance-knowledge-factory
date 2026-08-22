from pathlib import Path

from factory_core.canonical.waiting_period_material_rules_binding import WaitingPeriodMaterialRulesBinding
from factory_core.canonical.waiting_period_multispan_binding import WaitingPeriodMultispanBinding
from insurance_intelligence.rule_certification.waiting_period_material_rules import (
    build_waiting_period_material_rules_certification_case,
    run_waiting_period_material_rules_certification_case,
)
from insurance_intelligence.rule_certification.waiting_period_multispan import (
    build_waiting_period_multispan_certification_case,
    run_waiting_period_multispan_certification_case,
)


ROOT = Path(__file__).resolve().parents[2]
BASE_SPEC = ROOT / "docs/architecture/star_health_star_comprehensive_specified_disease_waiting_period_multispan_binding_spec.json"
MATERIAL_SPEC = ROOT / "docs/architecture/star_health_star_comprehensive_specified_disease_material_rules_spec.json"


def test_star_specified_disease_multispan_binding_preserves_both_exact_pages() -> None:
    result = WaitingPeriodMultispanBinding().bind_from_spec_file(spec_path=BASE_SPEC, repository_root=ROOT)
    manifest = result.manifest
    assert manifest["binding_type"] == "waiting_period_multispan_binding_v1"
    assert manifest["binding_status"] == "reviewed_waiting_period_bound_not_published"
    assert manifest["mechanism_evidence_span_count"] == 2
    assert manifest["publication_status"] == "bound_not_published"
    assert [(x["candidate_id"], x["source_page"], x["candidate_text_sha256"]) for x in manifest["evidence"]] == [
        ("candidate_page_31", 31, "b9f28db495943d84bbf6a900df47b18717c6300bf510f88786914ae28be11e77"),
        ("candidate_page_32", 32, "214466445fab2fd7fec30d951696479d4999bfc74aea13af40a1b80eddef77eb"),
    ]
    mechanic = manifest["mechanic"]
    assert mechanic["waiting_period_type"] == "SPECIFIC_DISEASE_PROCEDURE"
    assert (mechanic["duration_value"], mechanic["duration_unit"]) == (24, "MONTHS")
    assert mechanic["value_source"] == "PRODUCT_FIXED"
    assert mechanic["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    assert mechanic["exclusions_or_exceptions"] == ["claims_arising_due_to_an_accident"]


def test_star_specified_disease_multispan_certification_attributes_continuity_to_page_32() -> None:
    case = build_waiting_period_multispan_certification_case(binding_spec_path=BASE_SPEC.relative_to(ROOT), repository_root=ROOT)
    result = run_waiting_period_multispan_certification_case(case)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    by_topic = {}
    for package in case.evidence_output.evidence_packages:
        by_topic.setdefault(package.field_or_topic, []).append(package.page)
    assert by_topic["WAITING_PERIOD_DURATION"] == [31]
    assert by_topic["WAITING_PERIOD_SUBJECT"] == [31]
    assert by_topic["WAITING_PERIOD_START_BASIS"] == [31]
    assert by_topic["APPLICABILITY_SCOPE"] == [31]
    assert by_topic["CONTINUITY_OR_CREDIT_RULE"] == [32]
    assert by_topic["EXCEPTION_CONDITION"] == [31]


def test_star_specified_disease_material_rules_use_multispan_base_without_semantic_drift() -> None:
    binding = WaitingPeriodMaterialRulesBinding().bind_from_spec_file(spec_path=MATERIAL_SPEC, repository_root=ROOT)
    assert binding.manifest["material_rules_status"] == "reviewed_material_rules_bound_not_published"
    assert [(r["rule_type"], r["evidence_candidate_ids"]) for r in binding.manifest["material_rules"]] == [
        ("RELATIONSHIP_LONGER_OF", ["candidate_page_31"]),
        ("APPLICABILITY_CONDITION", ["candidate_page_32"]),
    ]
    case = build_waiting_period_material_rules_certification_case(binding_spec_path=MATERIAL_SPEC.relative_to(ROOT), repository_root=ROOT)
    result = run_waiting_period_material_rules_certification_case(case)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    pages = {package.field_or_topic: package.page for package in case.evidence_output.evidence_packages}
    assert pages["WAITING_PERIOD_RELATIONSHIP_RULE"] == 31
    assert pages["WAITING_PERIOD_APPLICABILITY_CONDITION"] == 32
