from __future__ import annotations

from dataclasses import fields

import pytest

from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey
from insurance_intelligence.generic_knowledge.dependency_resolution import (
    DependencyResolutionError,
    EffectiveDependencyState,
    ModifierDirection,
    ResolutionDependencyMode,
    ResolutionOperand,
    resolve_conditional_modifier,
    resolve_required_inputs,
    validate_dependency_path,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    ComputedResolution,
    ResolutionSeverity,
    ResolutionStatus,
)


def _resolution(status: ResolutionStatus) -> ComputedResolution:
    severity = {
        ResolutionStatus.RESOLVED: ResolutionSeverity.RESOLVED,
        ResolutionStatus.POLICY_SCHEDULE_BOUND: ResolutionSeverity.INSTANCE_BOUND,
        ResolutionStatus.INSTANCE_CONDITION_REQUIRED: ResolutionSeverity.INSTANCE_BOUND,
        ResolutionStatus.OPERAND_INSTANCE_BOUND: ResolutionSeverity.INSTANCE_BOUND,
        ResolutionStatus.REVIEW_REQUIRED: ResolutionSeverity.GOVERNANCE_BLOCKED,
        ResolutionStatus.SOURCE_STALE: ResolutionSeverity.GOVERNANCE_BLOCKED,
        ResolutionStatus.REGULATORY_VERIFICATION_REQUIRED: ResolutionSeverity.GOVERNANCE_BLOCKED,
        ResolutionStatus.OPERAND_GOVERNANCE_BLOCKED: ResolutionSeverity.GOVERNANCE_BLOCKED,
        ResolutionStatus.NOT_YET_REPRESENTABLE: ResolutionSeverity.REPRESENTATIONALLY_BLOCKED,
        ResolutionStatus.SEMANTIC_CONFLICT: ResolutionSeverity.REPRESENTATIONALLY_BLOCKED,
        ResolutionStatus.OPERAND_REPRESENTATIONALLY_BLOCKED: ResolutionSeverity.REPRESENTATIONALLY_BLOCKED,
        ResolutionStatus.VALIDATION_CONFLICT: ResolutionSeverity.VALIDATION_BLOCKED,
    }[status]
    return ComputedResolution(status=status, severity=severity)


def _cell(*, variant: str = "base") -> ApplicabilityKey:
    return ApplicabilityKey(product_reference="generic:test", variant=variant)


def _operand(operand_id: str, status: ResolutionStatus, *, variant: str = "base") -> ResolutionOperand:
    return ResolutionOperand(
        operand_id=operand_id,
        resolution=_resolution(status),
        applicability=_cell(variant=variant),
    )


def test_required_inputs_all_resolved_are_fully_resolved() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.RESOLVED),
        _operand("specific", ResolutionStatus.RESOLVED),
    ))
    assert result.mode is ResolutionDependencyMode.REQUIRED_INPUT
    assert result.effective_state is EffectiveDependencyState.FULLY_RESOLVED
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.RESOLVED
    assert result.causes == ()


def test_required_input_schedule_bound_is_operand_instance_bound() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.RESOLVED),
        _operand("specific", ResolutionStatus.POLICY_SCHEDULE_BOUND),
    ))
    assert result.effective_state is EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_INSTANCE_BOUND
    assert [(c.operand_id, c.status, c.primary) for c in result.causes] == [
        ("specific", ResolutionStatus.POLICY_SCHEDULE_BOUND, True)
    ]


def test_two_instance_bound_operands_preserve_both_causes() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.POLICY_SCHEDULE_BOUND),
        _operand("specific", ResolutionStatus.INSTANCE_CONDITION_REQUIRED),
    ))
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_INSTANCE_BOUND
    assert [cause.operand_id for cause in result.causes] == ["ped", "specific"]
    assert all(cause.primary for cause in result.causes)


def test_representation_block_dominates_instance_bound() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.POLICY_SCHEDULE_BOUND),
        _operand("specific", ResolutionStatus.NOT_YET_REPRESENTABLE),
    ))
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_REPRESENTATIONALLY_BLOCKED
    primary = [c for c in result.causes if c.primary]
    secondary = [c for c in result.causes if not c.primary]
    assert [(c.operand_id, c.status) for c in primary] == [
        ("specific", ResolutionStatus.NOT_YET_REPRESENTABLE)
    ]
    assert [(c.operand_id, c.status) for c in secondary] == [
        ("ped", ResolutionStatus.POLICY_SCHEDULE_BOUND)
    ]


def test_governance_block_dominates_instance_bound() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.POLICY_SCHEDULE_BOUND),
        _operand("specific", ResolutionStatus.REVIEW_REQUIRED),
    ))
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_GOVERNANCE_BLOCKED
    assert next(c for c in result.causes if c.primary).status is ResolutionStatus.REVIEW_REQUIRED


def test_source_stale_propagates_as_governance_block() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.SOURCE_STALE),
        _operand("specific", ResolutionStatus.RESOLVED),
    ))
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_GOVERNANCE_BLOCKED
    assert result.causes[0].status is ResolutionStatus.SOURCE_STALE


def test_regulatory_verification_propagates_as_governance_block() -> None:
    result = resolve_required_inputs((
        _operand("migration", ResolutionStatus.REGULATORY_VERIFICATION_REQUIRED),
    ))
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_GOVERNANCE_BLOCKED


def test_semantic_conflict_propagates_as_representation_block() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.SEMANTIC_CONFLICT),
    ))
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_REPRESENTATIONALLY_BLOCKED


def test_validation_conflict_dominates_required_inputs() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.VALIDATION_CONFLICT),
        _operand("specific", ResolutionStatus.NOT_YET_REPRESENTABLE),
    ))
    assert result.effective_state is EffectiveDependencyState.VALIDATION_CONFLICT
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_incompatible_applicability_cells_fail_closed() -> None:
    result = resolve_required_inputs((
        _operand("ped", ResolutionStatus.RESOLVED, variant="plan_a"),
        _operand("specific", ResolutionStatus.RESOLVED, variant="plan_b"),
    ))
    assert result.effective_state is EffectiveDependencyState.VALIDATION_CONFLICT
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_reducing_modifier_with_unknown_instance_condition_preserves_known_base_as_range() -> None:
    result = resolve_conditional_modifier(
        base=_operand("maternity_base", ResolutionStatus.RESOLVED),
        modifier=_operand("upfront_reduction", ResolutionStatus.INSTANCE_CONDITION_REQUIRED),
        direction=ModifierDirection.REDUCES,
    )
    assert result.mode is ResolutionDependencyMode.CONDITIONAL_MODIFIER
    assert result.effective_state is EffectiveDependencyState.CONDITIONAL_RANGE
    assert result.base_resolution is not None
    assert result.base_resolution.status is ResolutionStatus.RESOLVED
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.INSTANCE_CONDITION_REQUIRED


def test_unresolved_waiver_keeps_conservative_base() -> None:
    result = resolve_conditional_modifier(
        base=_operand("ped_base", ResolutionStatus.RESOLVED),
        modifier=_operand("chronic_care_waiver", ResolutionStatus.INSTANCE_CONDITION_REQUIRED),
        direction=ModifierDirection.WAIVES,
    )
    assert result.effective_state is EffectiveDependencyState.CONSERVATIVE_BASE_APPLIES
    assert result.base_resolution is not None
    assert result.base_resolution.status is ResolutionStatus.RESOLVED


def test_unresolved_override_keeps_conservative_base() -> None:
    result = resolve_conditional_modifier(
        base=_operand("base", ResolutionStatus.RESOLVED),
        modifier=_operand("override", ResolutionStatus.INSTANCE_CONDITION_REQUIRED),
        direction=ModifierDirection.REPLACES,
    )
    assert result.effective_state is EffectiveDependencyState.CONSERVATIVE_BASE_APPLIES


def test_resolved_modifier_can_be_fully_resolved_without_doing_value_arithmetic() -> None:
    result = resolve_conditional_modifier(
        base=_operand("base", ResolutionStatus.RESOLVED),
        modifier=_operand("modifier", ResolutionStatus.RESOLVED),
        direction=ModifierDirection.REDUCES,
    )
    assert result.effective_state is EffectiveDependencyState.FULLY_RESOLVED
    assert not hasattr(result, "resolved_value")


def test_unresolved_base_cannot_be_rescued_by_conditional_modifier() -> None:
    result = resolve_conditional_modifier(
        base=_operand("base", ResolutionStatus.POLICY_SCHEDULE_BOUND),
        modifier=_operand("modifier", ResolutionStatus.RESOLVED),
        direction=ModifierDirection.REDUCES,
    )
    assert result.effective_state is EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_INSTANCE_BOUND


def test_representationally_blocked_modifier_does_not_masquerade_as_conditional_range() -> None:
    result = resolve_conditional_modifier(
        base=_operand("base", ResolutionStatus.RESOLVED),
        modifier=_operand("modifier", ResolutionStatus.NOT_YET_REPRESENTABLE),
        direction=ModifierDirection.REDUCES,
    )
    assert result.effective_state is EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    assert result.dependency_resolution is not None
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_REPRESENTATIONALLY_BLOCKED


def test_conditional_modifier_cell_mismatch_is_validation_conflict() -> None:
    result = resolve_conditional_modifier(
        base=_operand("base", ResolutionStatus.RESOLVED, variant="a"),
        modifier=_operand("modifier", ResolutionStatus.INSTANCE_CONDITION_REQUIRED, variant="b"),
        direction=ModifierDirection.WAIVES,
    )
    assert result.effective_state is EffectiveDependencyState.VALIDATION_CONFLICT


def test_dependency_mode_defaults_can_remain_non_propagating() -> None:
    assert ResolutionDependencyMode.NONE.value == "NONE"
    assert ResolutionDependencyMode.REQUIRED_INPUT.value == "REQUIRED_INPUT"
    assert ResolutionDependencyMode.CONDITIONAL_MODIFIER.value == "CONDITIONAL_MODIFIER"


def test_required_inputs_reject_empty_operands() -> None:
    with pytest.raises(DependencyResolutionError, match="must not be empty"):
        resolve_required_inputs(())


def test_required_inputs_reject_duplicate_operand_ids() -> None:
    with pytest.raises(DependencyResolutionError, match="must be unique"):
        resolve_required_inputs((
            _operand("ped", ResolutionStatus.RESOLVED),
            _operand("ped", ResolutionStatus.RESOLVED),
        ))


def test_conditional_modifier_rejects_same_operand_identity() -> None:
    with pytest.raises(DependencyResolutionError, match="must differ"):
        resolve_conditional_modifier(
            base=_operand("same", ResolutionStatus.RESOLVED),
            modifier=_operand("same", ResolutionStatus.INSTANCE_CONDITION_REQUIRED),
            direction=ModifierDirection.WAIVES,
        )


def test_self_cycle_rejected() -> None:
    with pytest.raises(DependencyResolutionError, match="cycle"):
        validate_dependency_path(("a", "a"))


def test_multi_node_cycle_rejected() -> None:
    with pytest.raises(DependencyResolutionError, match="cycle"):
        validate_dependency_path(("a", "b", "c", "a"))


def test_dependency_depth_cap_rejected() -> None:
    with pytest.raises(DependencyResolutionError, match="maximum depth"):
        validate_dependency_path(("a", "b", "c"), max_depth=2)


def test_effective_status_is_not_caller_authored() -> None:
    names = {field.name for field in fields(ResolutionOperand)}
    assert "effective_state" not in names
    assert "status" not in names


def test_c2_contract_has_no_product_identity_fields() -> None:
    operand_fields = {field.name for field in fields(ResolutionOperand)}
    result_fields = {field.name for field in fields(__import__(
        "insurance_intelligence.generic_knowledge.dependency_resolution",
        fromlist=["EffectiveDependencyResolution"],
    ).EffectiveDependencyResolution)}
    forbidden = {"insurer_id", "product_id", "uin"}
    assert forbidden.isdisjoint(operand_fields)
    assert forbidden.isdisjoint(result_fields)


def test_c2_contract_exposes_no_numeric_insurance_arithmetic() -> None:
    from insurance_intelligence.generic_knowledge import dependency_resolution as module

    source_names = set(module.__dict__)
    assert "longer_of" not in source_names
    assert "max_waiting_period" not in source_names
    assert "subtract_duration" not in source_names
