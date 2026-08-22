from pathlib import Path

import pytest

from factory_core.canonical.waiting_period_binding import WaitingPeriodBinding
from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodContractError,
    WaitingPeriodDurationUnit,
    WaitingPeriodMechanic,
    WaitingPeriodScopeType,
    WaitingPeriodStartBasis,
    WaitingPeriodType,
)
from insurance_intelligence.rule_certification.waiting_period import (
    build_waiting_period_certification_case,
    run_waiting_period_certification_case,
)
from insurance_intelligence.rule_certification.waiting_period_material_rules import (
    build_waiting_period_material_rules_certification_case,
    run_waiting_period_material_rules_certification_case,
)


ROOT = Path(__file__).resolve().parents[2]
DELIVERY = Path("docs/architecture/star_health_star_comprehensive_delivery_newborn_waiting_period_binding_spec.json")
DELIVERY_RULES = Path("docs/architecture/star_health_star_comprehensive_delivery_newborn_material_rules_spec.json")
BARIATRIC = Path("docs/architecture/star_health_star_comprehensive_bariatric_waiting_period_binding_spec.json")
PREVENTIVE = Path("docs/architecture/star_health_star_comprehensive_preventive_health_checkup_waiting_period_binding_spec.json")
PREVENTIVE_RULES = Path("docs/architecture/star_health_star_comprehensive_preventive_health_checkup_material_rules_spec.json")


def test_benefit_specific_type_requires_benefit_scope() -> None:
    with pytest.raises(WaitingPeriodContractError, match="BENEFIT_SPECIFIC requires BENEFIT_SCOPED scope"):
        WaitingPeriodMechanic(
            waiting_period_type=WaitingPeriodType.BENEFIT_SPECIFIC,
            duration_value=30,
            duration_unit=WaitingPeriodDurationUnit.DAYS,
            start_basis=WaitingPeriodStartBasis.POLICY_INCEPTION,
            applies_to=("some_benefit",),
            evidence_reference_ids=("evidence:1",),
            scope_type=WaitingPeriodScopeType.POLICY_WIDE,
        )


def _binding(relative: Path):
    return WaitingPeriodBinding().bind_from_spec_file(spec_path=ROOT / relative, repository_root=ROOT).manifest


def _certify(relative: Path):
    case = build_waiting_period_certification_case(binding_spec_path=relative, repository_root=ROOT)
    return case, run_waiting_period_certification_case(case)


def test_star_delivery_newborn_is_generic_benefit_scoped_waiting_period() -> None:
    manifest = _binding(DELIVERY)
    mechanic = manifest["mechanic"]
    assert mechanic["waiting_period_type"] == "BENEFIT_SPECIFIC"
    assert mechanic["scope_type"] == "BENEFIT_SCOPED"
    assert mechanic["scope_reference"] == "section_ii_14_delivery_and_new_born"
    assert (mechanic["duration_value"], mechanic["duration_unit"]) == (24, "MONTHS")
    assert manifest["evidence"][0]["candidate_id"] == "candidate_page_14"
    case, result = _certify(DELIVERY)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert all(package.page == 14 for package in case.evidence_output.evidence_packages)


def test_star_delivery_newborn_reset_after_event_is_certified_separately() -> None:
    case = build_waiting_period_material_rules_certification_case(
        binding_spec_path=DELIVERY_RULES,
        repository_root=ROOT,
    )
    result = run_waiting_period_material_rules_certification_case(case)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    checks = {check.component_id: check for check in result.component_checks}
    assert checks["reset_after_event"].passed is True
    assert checks["applicability_condition"].passed is True
    packages = {package.field_or_topic: package for package in case.evidence_output.evidence_packages}
    assert packages["WAITING_PERIOD_RESET_AFTER_EVENT"].page == 14
    assert "applies afresh" in packages["WAITING_PERIOD_RESET_AFTER_EVENT"].claim
    assert packages["WAITING_PERIOD_APPLICABILITY_CONDITION"].page == 14


def test_star_bariatric_wait_is_benefit_scoped_without_importing_medical_eligibility() -> None:
    manifest = _binding(BARIATRIC)
    mechanic = manifest["mechanic"]
    assert mechanic["waiting_period_type"] == "BENEFIT_SPECIFIC"
    assert mechanic["scope_reference"] == "section_ii_15_bariatric_surgery"
    assert (mechanic["duration_value"], mechanic["duration_unit"]) == (36, "MONTHS")
    assert manifest["evidence"][0]["candidate_id"] == "candidate_page_15"
    _, result = _certify(BARIATRIC)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"


def test_star_preventive_health_checkup_wait_and_renewal_rule_are_certified() -> None:
    manifest = _binding(PREVENTIVE)
    mechanic = manifest["mechanic"]
    assert mechanic["waiting_period_type"] == "BENEFIT_SPECIFIC"
    assert mechanic["scope_reference"] == "section_ii_18_preventive_health_checkup"
    assert (mechanic["duration_value"], mechanic["duration_unit"]) == (30, "DAYS")
    assert manifest["evidence"][0]["candidate_id"] == "candidate_page_16"
    _, scalar = _certify(PREVENTIVE)
    assert scalar.outcome == "PASS"
    assert scalar.actual_completeness_status == "COMPLETE"

    case = build_waiting_period_material_rules_certification_case(
        binding_spec_path=PREVENTIVE_RULES,
        repository_root=ROOT,
    )
    material = run_waiting_period_material_rules_certification_case(case)
    assert material.outcome == "PASS"
    assert material.actual_completeness_status == "COMPLETE"
    package = next(
        item for item in case.evidence_output.evidence_packages
        if item.field_or_topic == "WAITING_PERIOD_APPLICABILITY_CONDITION"
    )
    assert package.page == 16
    assert "does not apply during subsequent renewals" in package.claim
