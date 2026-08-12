from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey
from insurance_intelligence.generic_knowledge.dependency_resolution import (
    EffectiveDependencyState,
    ModifierDirection,
    ResolutionOperand,
    resolve_conditional_modifier,
    resolve_required_inputs,
)
from insurance_intelligence.generic_knowledge.governance_integration import (
    AnswerShape,
    RegulatoryEffectClass,
    RegulatoryInterpretationState,
    assess_regulatory_interpretation,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    ResolutionInputs,
    ResolutionStatus,
    ValueSource,
    compute_resolution_status,
)


CLOSURE = Path(
    "docs/architecture/MO_028B_G11_BAJAJ_ADVERSARIAL_CLOSURE_CERTIFICATION.json"
)
C6_4 = Path(
    "docs/architecture/MO_028B_G11_C6_4_BAJAJ_SCHEDULE_BOUND_BASE_MECHANIC_ADJUDICATION.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g11_closure_records_zero_semantic_residue_without_claiming_full_resolution() -> None:
    closure = _load(CLOSURE)
    representation = closure["semantic_representability"]
    resolution = closure["resolution_safety"]
    assert representation["atomic_unit_count"] == 30
    assert representation["accounted_unit_count"] == 30
    assert representation["true_semantic_residue_count"] == 0
    assert representation["complete"] is True
    assert resolution["all_customer_answers_resolved"] is False


def test_g11_closure_matches_c6_4_zero_residue_adjudication() -> None:
    closure = _load(CLOSURE)["semantic_representability"]
    c6_4 = _load(C6_4)["revised_c6_summary"]
    assert closure["atomic_unit_count"] == c6_4["atomic_unit_count"] == 30
    assert closure["accounted_unit_count"] == c6_4["accounted_unit_count"] == 30
    assert closure["true_semantic_residue_count"] == c6_4["true_semantic_residue_count"] == 0


def test_schedule_selected_wait_remains_policy_schedule_bound_without_instance_value() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    assert resolution.status is ResolutionStatus.POLICY_SCHEDULE_BOUND
    closure = _load(CLOSURE)["resolution_safety"]["policy_schedule_selected_waits"]
    assert closure["status_without_instance_schedule"] == resolution.status.value
    assert set(closure["affected_types"]) == {
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
    }


def test_longer_of_relationship_is_accounted_but_instance_bound_until_required_operands_resolve() -> None:
    applicability = ApplicabilityKey(product_reference="product://bajaj-adversarial")
    instance_bound = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    result = resolve_required_inputs(
        (
            ResolutionOperand("ped", instance_bound, applicability, resolution_cell_identity=("wp", "base")),
            ResolutionOperand("specific", instance_bound, applicability, resolution_cell_identity=("wp", "base")),
        )
    )
    assert result.effective_state is EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_INSTANCE_BOUND
    closure = _load(CLOSURE)["resolution_safety"]["longer_of_dependency"]
    assert closure["accounting_state"] == "MAPPED_AS_RELATIONSHIP"
    assert closure["status_before_required_schedule_operands_resolve"] == "OPERAND_INSTANCE_BOUND"


def test_maternity_and_baby_modifiers_remain_conditional_not_scalar_when_instance_condition_missing() -> None:
    applicability = ApplicabilityKey(product_reference="product://bajaj-adversarial")
    base = compute_resolution_status(ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED))
    modifier = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_INSTANCE_CONDITION,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    result = resolve_conditional_modifier(
        base=ResolutionOperand("base", base, applicability, resolution_cell_identity=("wp", "conditional")),
        modifier=ResolutionOperand("modifier", modifier, applicability, resolution_cell_identity=("wp", "conditional")),
        direction=ModifierDirection.REDUCES,
    )
    assert result.effective_state is EffectiveDependencyState.CONDITIONAL_RANGE
    closure = _load(CLOSURE)["resolution_safety"]["conditional_modifiers"]
    assert closure["state_without_instance_condition"] == "CONDITIONAL_RANGE"
    assert set(closure["affected_types"]) == {"MATERNITY", "BABY_CARE"}


def test_migration_effective_credit_remains_fail_closed_and_unquantified() -> None:
    assessment = assess_regulatory_interpretation(
        verification_required=True,
        effect_class=RegulatoryEffectClass.BENEFIT_ESTABLISHING,
    )
    assert assessment.state is RegulatoryInterpretationState.VERIFICATION_REQUIRED
    assert assessment.answer_shape is AnswerShape.UNQUANTIFIED
    assert assessment.contract_fact_publishable is False
    migration = _load(CLOSURE)["resolution_safety"]["migration"]
    assert migration["regulatory_effect_class"] == "BENEFIT_ESTABLISHING"
    assert migration["effective_credit_status"] == "REGULATORY_VERIFICATION_REQUIRED"
    assert migration["answer_shape"] == "UNQUANTIFIED"
    assert migration["affirmative_effective_benefit_publishable"] is False


def test_zero_residue_never_implies_automatic_publication() -> None:
    closure = _load(CLOSURE)["publication_safety"]
    assert closure["zero_residue_implies_publication_ready"] is False
    assert closure["semantic_representation_complete"] is True
    assert closure["publication_requires_existing_g7_c5_governance_gates"] is True
    assert closure["human_review_still_required_where_configured"] is True
    assert closure["source_freshness_still_required"] is True
    assert closure["authority_resolution_still_required"] is True
    assert closure["publication_certified_in_this_artifact"] is False


def test_instance_bound_states_are_not_reintroduced_as_semantic_residue() -> None:
    closure = _load(CLOSURE)
    assert closure["semantic_representability"]["true_semantic_residue_count"] == 0
    assert closure["publication_safety"]["instance_bound_states_are_not_semantic_residue"] is True
    assert closure["resolution_safety"]["policy_schedule_selected_waits"]["status_without_instance_schedule"] == "POLICY_SCHEDULE_BOUND"


def test_g11_closure_preserves_genericity_and_adds_no_product_reasoning() -> None:
    genericity = _load(CLOSURE)["genericity"]
    assert genericity == {
        "product_identity_reasoning_code_added": False,
        "mixed_accounting_added": False,
        "product_specific_semantic_type_added": False,
        "new_parallel_governance_engine_added": False,
    }


def test_g11_closure_is_certification_gate_not_publication_decision() -> None:
    decision = _load(CLOSURE)["decision"]
    assert decision["g11_adversarial_semantic_generalization_complete"] is True
    assert decision["g11_ready_for_closure_certification_tests"] is True
    assert decision["g11_closed"] is False
    assert "MO-028B Health Generalization Certification" in decision["next_action_after_green_tests"]
