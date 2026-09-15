from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.publication_decision.governed import (
    build_governed_publication_context,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_generic_governed_publication_accepts_existing_rule_certification_fixture(tmp_path: Path) -> None:
    """D0 falsification: a non-copay certified rule must enter generic publication without product code.

    The Star initial waiting-period case already passes the generic RuleCertificationRunner.
    Publication should be able to consume that existing fixture through a generic fixture strategy,
    rather than requiring a co-pay binding strategy or a Star-specific publication module.
    """
    spec = {
        "schema_version": "1.0",
        "publication_spec_type": "governed_assertion_publication_v1",
        "certification": {
            "strategy": "rule_certification_fixture_v1",
            "fixture_module": "insurance_intelligence.rule_certification.star_health_initial_waiting_period",
            "fixture_factory": "build_star_comprehensive_initial_waiting_period_case",
            "domain": "health",
        },
    }
    relative = "tmp_d0_waiting_period_publication_spec.json"
    path = REPOSITORY_ROOT / relative
    try:
        path.write_text(json.dumps(spec), encoding="utf-8")
        loaded_spec, case, result = build_governed_publication_context(
            publication_spec_path=relative,
            repository_root=REPOSITORY_ROOT,
        )
    finally:
        if path.exists():
            path.unlink()

    assert loaded_spec["certification"]["strategy"] == "rule_certification_fixture_v1"
    assert case.case_id == "star_comprehensive_initial_waiting_period"
    assert case.expectation.topic_id == "waiting_period"
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
