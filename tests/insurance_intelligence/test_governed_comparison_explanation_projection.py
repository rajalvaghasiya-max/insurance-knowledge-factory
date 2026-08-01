from dataclasses import replace
from datetime import date

import pytest

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import RESTORATION_CONCEPT_ID
from insurance_intelligence.benefits.explanation_projection import (
    ComparisonExplanationProjectionError,
    ExplanationMechanic,
    ExplanationProjectionStatus,
    ExplanationSide,
    GovernedComparisonExplanationProjection,
    project_comparison_explanation,
)
from insurance_intelligence.benefits.orchestration import (
    ComparisonOrchestrationStatus,
    GovernedComparisonRequest,
    orchestrate_governed_comparison,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


AS_OF = date(2026, 8, 1)
LEFT_ID = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.implementation_id
RIGHT_ID = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.implementation_id
REGISTRY = (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)


def _outcome(**request_overrides):
    values = {
        "concept_id": RESTORATION_CONCEPT_ID,
        "left_implementation_id": LEFT_ID,
        "right_implementation_id": RIGHT_ID,
        "as_of": AS_OF,
    }
    values.update(request_overrides)
    request = GovernedComparisonRequest(**values)
    return orchestrate_governed_comparison(request, registry=REGISTRY)


def _projection():
    return project_comparison_explanation(_outcome())


def test_projection_rejects_wrong_input_type():
    with pytest.raises(ComparisonExplanationProjectionError):
        project_comparison_explanation("not-an-outcome")


def test_real_pair_is_ready_with_source_limitations():
    result = _projection()
    assert result.status is ExplanationProjectionStatus.READY_WITH_SOURCE_LIMITATIONS
    assert result.orchestration_status is ComparisonOrchestrationStatus.PARTIAL_SOURCE_ELIGIBILITY
    assert result.is_ready is True


def test_projection_preserves_request_context():
    result = _projection()
    assert result.concept_id == RESTORATION_CONCEPT_ID
    assert result.as_of == AS_OF
    assert result.left.implementation_id == LEFT_ID
    assert result.right.implementation_id == RIGHT_ID


def test_projection_preserves_side_product_identities():
    result = _projection()
    assert result.left.insurer_id == "star_health"
    assert result.left.product_id == "star_comprehensive"
    assert result.right.insurer_id == "aditya_birla_health"
    assert result.right.product_id == "activ_one_nxt"


def test_shared_mechanics_are_deterministically_ordered():
    result = _projection()
    ids = tuple(item.dimension_id for item in result.shared_mechanics)
    assert ids == tuple(sorted(ids))
    assert "restoration_amount_percentage_per_activation" in ids
    assert "policy_year_reset" in ids


def test_different_mechanics_include_frequency_type():
    result = _projection()
    by_id = {item.dimension_id: item for item in result.different_mechanics}
    frequency = by_id["restoration_frequency_type"]
    assert frequency.left_value == "FINITE"
    assert frequency.right_value == "UNLIMITED"


def test_different_mechanics_include_same_hospitalization_use():
    result = _projection()
    by_id = {item.dimension_id: item for item in result.different_mechanics}
    mechanic = by_id["same_hospitalization_use"]
    assert mechanic.left_value is False
    assert mechanic.right_value is True


def test_left_only_mechanics_are_projected():
    result = _projection()
    ids = {item.dimension_id for item in result.left_only_mechanics}
    assert {
        "same_illness_use",
        "relapse_window_days",
        "carry_over_between_policy_years",
    } <= ids


def test_right_only_mechanics_are_projected():
    result = _projection()
    ids = {item.dimension_id for item in result.right_only_mechanics}
    assert {
        "first_claim_use",
        "partial_restoration_use",
        "maximum_liability_per_claim_percentage",
        "utilization_sequence",
    } <= ids


def test_real_pair_has_no_blocked_mechanics():
    assert _projection().blocked_mechanics == ()


def test_projection_preserves_evidence_references():
    result = _projection()
    item = next(
        mechanic
        for mechanic in result.different_mechanics
        if mechanic.dimension_id == "restoration_frequency_type"
    )
    assert item.left_evidence_reference_ids
    assert item.right_evidence_reference_ids
    assert item.left_source_dimension_ids == ("restoration_count_per_policy_period",)
    assert item.right_source_dimension_ids == ("restoration_count_per_policy_period",)


def test_projection_preserves_orchestration_reasons():
    outcome = _outcome()
    result = project_comparison_explanation(outcome)
    assert result.reasons == outcome.reasons


def test_projection_adds_non_advisory_limitations():
    joined = " ".join(_projection().limitations).lower()
    assert "not generated advice" in joined
    assert "do not indicate product superiority" in joined
    assert "not ranking signals" in joined
    assert "suitability" in joined


def test_blocked_outcome_projects_without_mechanics():
    outcome = _outcome(left_implementation_id="benefit_impl:missing:left")
    result = project_comparison_explanation(outcome)
    assert result.status is ExplanationProjectionStatus.BLOCKED
    assert result.is_ready is False
    assert result.shared_mechanics == ()
    assert result.different_mechanics == ()
    assert result.left_only_mechanics == ()
    assert result.right_only_mechanics == ()
    assert result.blocked_mechanics == ()


def test_blocked_projection_preserves_requested_identities():
    missing = "benefit_impl:missing:left"
    result = project_comparison_explanation(_outcome(left_implementation_id=missing))
    assert result.left.implementation_id == missing
    assert result.left.insurer_id is None
    assert result.right.implementation_id == RIGHT_ID


def test_blocked_projection_preserves_reasons_and_limitations():
    outcome = _outcome(left_implementation_id="benefit_impl:missing:left")
    result = project_comparison_explanation(outcome)
    assert result.reasons == outcome.reasons
    assert set(outcome.limitations) <= set(result.limitations)


def test_explanation_side_rejects_empty_identity():
    with pytest.raises(ComparisonExplanationProjectionError):
        ExplanationSide(" ", None, None, None)


def test_explanation_side_rejects_empty_optional_identity():
    with pytest.raises(ComparisonExplanationProjectionError):
        ExplanationSide("implementation", " ", None, None)


def test_explanation_mechanic_rejects_empty_dimension():
    with pytest.raises(ComparisonExplanationProjectionError):
        ExplanationMechanic(" ", None, None, None, (), (), (), ())


def test_explanation_mechanic_rejects_non_tuple_lineage():
    with pytest.raises(ComparisonExplanationProjectionError):
        ExplanationMechanic("dimension", None, None, None, [], (), (), ())


def test_projection_contract_rejects_unsorted_mechanics():
    second = ExplanationMechanic("z_dimension", 1, 1, None, (), (), (), ())
    first = ExplanationMechanic("a_dimension", 1, 1, None, (), (), (), ())
    base = _projection()
    with pytest.raises(ComparisonExplanationProjectionError):
        replace(base, shared_mechanics=(second, first))


def test_blocked_projection_contract_rejects_mechanics():
    blocked = project_comparison_explanation(
        _outcome(left_implementation_id="benefit_impl:missing:left")
    )
    mechanic = ExplanationMechanic("dimension", 1, 1, None, (), (), (), ())
    with pytest.raises(ComparisonExplanationProjectionError):
        replace(blocked, shared_mechanics=(mechanic,))


def test_projection_status_helper_handles_completed_outcome():
    partial = _outcome()
    completed = replace(partial, status=ComparisonOrchestrationStatus.COMPLETED)
    result = project_comparison_explanation(completed)
    assert result.status is ExplanationProjectionStatus.READY
    assert result.is_ready is True


def test_projection_does_not_mutate_source_outcome():
    outcome = _outcome()
    original_dimensions = outcome.comparison.dimensions
    project_comparison_explanation(outcome)
    assert outcome.comparison.dimensions == original_dimensions
