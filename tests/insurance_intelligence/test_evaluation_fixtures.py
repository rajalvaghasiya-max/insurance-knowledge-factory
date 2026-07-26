from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.evaluation.fixtures import (
    EvaluationFixtureError,
    PipelineFixtureRegistry,
    build_default_fixture_registry,
    build_default_fixtures,
    build_fixture,
)
from insurance_intelligence.evaluation.scenarios import build_default_registry


def _scenario(scenario_id="star_copay_general_explanation"):
    return build_default_registry().get(scenario_id)


def test_build_fixture_is_deterministic():
    first = build_fixture(_scenario())
    second = build_fixture(_scenario())
    assert first == second
    assert first.fixture_id == "fixture:star_copay_general_explanation:1.0"
    assert first.request_id == "eval:star_copay_general_explanation:1.0"


def test_fixture_preserves_scenario_request_and_scope():
    fixture = build_fixture(_scenario())
    assert fixture.request_text == "What does this conditional co-payment clause mean?"
    assert fixture.domain == "health"
    assert fixture.topic == "conditional_copayment"
    assert fixture.audience == "CUSTOMER"


def test_default_repository_root_is_explicit():
    fixture = build_fixture(_scenario())
    assert fixture.repository_roots == ("knowledge/factory/registry_backed",)


def test_empty_repository_roots_are_rejected():
    with pytest.raises(EvaluationFixtureError, match="must not be empty"):
        build_fixture(_scenario(), repository_roots=())


def test_duplicate_repository_roots_are_rejected():
    with pytest.raises(EvaluationFixtureError, match="unique"):
        build_fixture(_scenario(), repository_roots=("a", "a"))


def test_unknown_fixture_state_is_rejected():
    with pytest.raises(EvaluationFixtureError, match="fixture_state"):
        build_fixture(_scenario(), fixture_state="BROKEN")


def test_unknown_trigger_state_is_rejected():
    with pytest.raises(EvaluationFixtureError, match="trigger_state"):
        build_fixture(_scenario(), trigger_state="MAYBE")


def test_unknown_strict_mode_is_rejected():
    with pytest.raises(EvaluationFixtureError, match="strict_mode"):
        build_fixture(_scenario(), strict_mode="LOOSE")


def test_repeat_count_must_be_positive_integer():
    with pytest.raises(EvaluationFixtureError, match="positive integer"):
        build_fixture(_scenario(), repeat_count=0)
    with pytest.raises(EvaluationFixtureError, match="positive integer"):
        build_fixture(_scenario(), repeat_count=True)


def test_confirmed_trigger_is_explicit_approved_context():
    fixture = build_fixture(_scenario("star_copay_trigger_confirmed"), trigger_state="CONFIRMED")
    assert fixture.trigger_state == "CONFIRMED"
    assert fixture.approved_context["copayment_trigger_status"] == "CONFIRMED"


def test_disproved_trigger_is_explicit_approved_context():
    fixture = build_fixture(_scenario("star_copay_trigger_disproved"), trigger_state="DISPROVED")
    assert fixture.approved_context["copayment_trigger_status"] == "DISPROVED"


def test_unspecified_trigger_removes_hidden_trigger_context():
    fixture = build_fixture(
        _scenario("star_copay_missing_trigger"),
        trigger_state="UNSPECIFIED",
        approved_context={"copayment_trigger_status": "CONFIRMED"},
    )
    assert "copayment_trigger_status" not in fixture.approved_context


def test_failed_lineage_fixture_state_is_explicit():
    fixture = build_default_fixture_registry().get("star_copay_failed_lineage")
    assert fixture.fixture_state == "FAILED_LINEAGE"
    assert fixture.approved_context["fixture_state"] == "FAILED_LINEAGE"


def test_version_unresolved_fixture_state_is_explicit():
    fixture = build_default_fixture_registry().get("star_copay_version_unresolved")
    assert fixture.fixture_state == "VERSION_UNRESOLVED"


def test_material_conflict_fixture_state_is_explicit():
    fixture = build_default_fixture_registry().get("star_copay_material_conflict")
    assert fixture.fixture_state == "MATERIAL_CONFLICT"


def test_unsupported_recommendation_fixture_state_is_explicit():
    fixture = build_default_fixture_registry().get("unsupported_product_recommendation")
    assert fixture.fixture_state == "UNSUPPORTED_RECOMMENDATION"


def test_customer_and_advisor_audiences_are_preserved():
    registry = build_default_fixture_registry()
    assert registry.get("star_copay_customer_format").audience == "CUSTOMER"
    assert registry.get("star_copay_advisor_format").audience == "ADVISOR"


def test_determinism_fixture_runs_twice():
    fixture = build_default_fixture_registry().get("star_copay_determinism")
    assert fixture.repeat_count == 2


def test_non_determinism_fixtures_run_once():
    fixtures = build_default_fixtures()
    assert all(item.repeat_count == 1 for item in fixtures if item.scenario_id != "star_copay_determinism")


def test_default_fixture_catalogue_covers_all_scenarios():
    scenario_ids = {item.scenario_id for item in build_default_registry().all_scenarios()}
    fixture_ids = {item.scenario_id for item in build_default_fixtures()}
    assert fixture_ids == scenario_ids
    assert len(fixture_ids) == 11


def test_registry_rejects_duplicate_scenario_fixture():
    fixture = build_fixture(_scenario())
    with pytest.raises(EvaluationFixtureError, match="duplicate"):
        PipelineFixtureRegistry((fixture, fixture))


def test_registry_get_rejects_unknown_scenario():
    with pytest.raises(EvaluationFixtureError, match="unknown scenario_id"):
        build_default_fixture_registry().get("missing")


def test_registry_order_is_deterministic():
    fixtures = build_default_fixtures()
    first = PipelineFixtureRegistry(reversed(fixtures)).all_fixtures()
    second = PipelineFixtureRegistry(fixtures).all_fixtures()
    assert first == second


def test_context_and_stage_overrides_are_immutable():
    fixture = build_fixture(_scenario(), stage_overrides={"EVIDENCE_RESOLVER": "FAILED_LINEAGE"})
    with pytest.raises(TypeError):
        fixture.approved_context["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        fixture.stage_overrides["new"] = "value"  # type: ignore[index]


def test_fixture_is_frozen():
    fixture = build_fixture(_scenario())
    with pytest.raises(FrozenInstanceError):
        fixture.fixture_id = "changed"  # type: ignore[misc]


def test_scenario_identity_is_preserved_in_context():
    fixture = build_fixture(_scenario())
    assert fixture.approved_context["scenario_id"] == fixture.scenario_id
    assert fixture.approved_context["scenario_version"] == fixture.scenario_version
