from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.publication_decision.governed import (
    GovernedPublicationSpecError,
    build_governed_publication_context,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _write_spec(name: str, certification: dict) -> str:
    relative = name
    (REPOSITORY_ROOT / relative).write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "publication_spec_type": "governed_assertion_publication_v1",
                "certification": certification,
            }
        ),
        encoding="utf-8",
    )
    return relative


def test_existing_waiting_period_fixture_runs_through_generic_publication_context() -> None:
    relative = _write_spec(
        "tmp_generic_waiting_period_publication_spec.json",
        {
            "strategy": "rule_certification_fixture_v1",
            "fixture_module": "insurance_intelligence.rule_certification.star_health_initial_waiting_period",
            "fixture_factory": "build_star_comprehensive_initial_waiting_period_case",
            "domain": "health",
        },
    )
    try:
        _, case, result = build_governed_publication_context(
            publication_spec_path=relative,
            repository_root=REPOSITORY_ROOT,
        )
    finally:
        (REPOSITORY_ROOT / relative).unlink(missing_ok=True)

    assert case.case_id == "star_comprehensive_initial_waiting_period"
    assert case.expectation.topic_id == "waiting_period"
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.limitations == case.evidence_output.limitations


def test_fixture_strategy_rejects_modules_outside_certification_namespace() -> None:
    relative = _write_spec(
        "tmp_invalid_fixture_publication_spec.json",
        {
            "strategy": "rule_certification_fixture_v1",
            "fixture_module": "insurance_intelligence.reasoning.rules",
            "fixture_factory": "build_rule_definition",
            "domain": "health",
        },
    )
    try:
        with pytest.raises(
            GovernedPublicationSpecError,
            match="must be under insurance_intelligence.rule_certification",
        ):
            build_governed_publication_context(
                publication_spec_path=relative,
                repository_root=REPOSITORY_ROOT,
            )
    finally:
        (REPOSITORY_ROOT / relative).unlink(missing_ok=True)
