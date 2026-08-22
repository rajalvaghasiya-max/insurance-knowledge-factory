from __future__ import annotations

import json
from pathlib import Path

from tests.factory_core.test_waiting_period_material_rules_binding import _fixture
from insurance_intelligence.rule_certification.waiting_period_material_rules import (
    build_waiting_period_material_rules_certification_case,
    run_waiting_period_material_rules_certification_case,
)


def test_certifies_post_wait_condition_from_exact_bound_candidate(tmp_path: Path) -> None:
    spec_path = _fixture(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["material_rules"] = [
        {
            "rule_id": "declared_and_accepted",
            "rule_type": "POST_WAIT_CONDITION",
            "statement": "Coverage after the waiting period requires prior declaration and insurer acceptance.",
            "related_waiting_period_type": None,
            "evidence_candidate_ids": ["candidate_page_1"],
        }
    ]
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    case = build_waiting_period_material_rules_certification_case(
        binding_spec_path=spec_path.name,
        repository_root=tmp_path,
    )
    result = run_waiting_period_material_rules_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    checks = {item.component_id: item for item in result.component_checks}
    assert checks["post_wait_condition"].passed is True
    package, = case.evidence_output.evidence_packages
    assert package.field_or_topic == "POST_WAIT_CONDITION"
    assert package.retrieval_basis[-1] == "candidate_page_1"
