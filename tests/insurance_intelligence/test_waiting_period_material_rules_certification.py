from __future__ import annotations

from pathlib import Path

from tests.factory_core.test_waiting_period_material_rules_binding import _fixture
from insurance_intelligence.rule_certification.waiting_period_material_rules import (
    build_waiting_period_material_rules_certification_case,
    run_waiting_period_material_rules_certification_case,
)


def test_certifies_relationship_and_applicability_rules_from_exact_bound_candidate(tmp_path: Path) -> None:
    spec_path = _fixture(tmp_path)
    case = build_waiting_period_material_rules_certification_case(binding_spec_path=spec_path.name, repository_root=tmp_path)
    result = run_waiting_period_material_rules_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    checks = {item.component_id: item for item in result.component_checks}
    assert checks["relationship_rule"].passed is True
    assert checks["applicability_condition"].passed is True

    packages = {item.field_or_topic: item for item in case.evidence_output.evidence_packages}
    assert packages["WAITING_PERIOD_RELATIONSHIP_RULE"].page == 1
    assert packages["WAITING_PERIOD_APPLICABILITY_CONDITION"].page == 1
    assert packages["WAITING_PERIOD_RELATIONSHIP_RULE"].retrieval_basis[-1] == "candidate_page_1"
