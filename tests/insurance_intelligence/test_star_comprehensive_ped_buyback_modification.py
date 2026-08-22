import json
from pathlib import Path

from factory_core.canonical.waiting_period_multispan_binding import WaitingPeriodMultispanBinding
from insurance_intelligence.rule_certification.waiting_period_modification import (
    build_waiting_period_modification_certification_case,
    run_waiting_period_modification_certification_case,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/architecture/star_health_star_comprehensive_ped_buyback_multispan_binding_spec.json"


def test_star_ped_buyback_binding_preserves_base_and_conditional_duration() -> None:
    result = WaitingPeriodMultispanBinding().bind_from_spec_file(spec_path=SPEC, repository_root=ROOT)
    mechanic = result.manifest["mechanic"]
    assert result.manifest["binding_status"] == "reviewed_waiting_period_bound_not_published"
    assert result.manifest["mechanism_evidence_span_count"] == 2
    assert (mechanic["duration_value"], mechanic["duration_unit"]) == (36, "MONTHS")
    assert mechanic["value_source"] == "PRODUCT_FIXED"
    assert len(mechanic["modifications"]) == 1
    modification = mechanic["modifications"][0]
    assert modification["modification_type"] == "REDUCTION"
    assert (modification["resulting_duration_value"], modification["resulting_duration_unit"]) == (12, "MONTHS")
    assert "first purchase" in modification["condition"]
    assert "not available at renewal" in modification["condition"]
    assert "ported from another insurer" in modification["condition"]
    assert modification["evidence_reference_ids"] == [
        "star_health_star_comprehensive_policy_wording_v1:candidate_page_30:19ec8a370e3269acb742a9a6e3e47a06d60d04cf20a8b743b65bca09b7735f9a"
    ]


def test_star_ped_buyback_modification_certifies_from_page_30_without_schedule_manufacturing() -> None:
    case = build_waiting_period_modification_certification_case(
        binding_spec_path=SPEC.relative_to(ROOT),
        repository_root=ROOT,
    )
    result = run_waiting_period_modification_certification_case(case)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    modification_packages = [
        package
        for package in case.evidence_output.evidence_packages
        if package.field_or_topic == "WAITING_PERIOD_MODIFICATION_RULE"
    ]
    assert len(modification_packages) == 1
    package = modification_packages[0]
    assert package.page == 30
    assert package.retrieval_basis[-1] == "candidate_page_30"
    assert "REDUCTION" in package.claim
    assert "12 MONTHS" in package.claim
    assert "first purchase" in package.claim


def test_star_ped_buyback_governance_does_not_infer_customer_selection() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    governance = spec["governance"]
    assert governance["publication_authorized"] is False
    assert governance["policy_specific_eligibility_authorized"] is False
    assert governance["optional_cover_selection_inferred_without_policy_evidence"] is False
    assert governance["customer_specific_12_month_wait_authorized_without_optional_cover_evidence"] is False
