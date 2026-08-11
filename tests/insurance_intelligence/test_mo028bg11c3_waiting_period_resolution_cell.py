from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodScopeType,
    WaitingPeriodType,
)
from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey
from insurance_intelligence.generic_knowledge.dependency_resolution import (
    EffectiveDependencyState,
    ResolutionOperand,
    resolve_required_inputs,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    ResolutionInputs,
    ResolutionStatus,
    ValueSource,
    compute_resolution_status,
)
from insurance_intelligence.generic_knowledge.waiting_period_resolution_cell import (
    AmountPortionIdentity,
    AmountPortionKind,
    ContinuitySource,
    PersonEventTiming,
    WaitingPeriodResolutionCell,
    WaitingPeriodResolutionCellError,
    cells_compatible_for_dependency_join,
    conservative_continuity_source,
    continuity_resolution,
)


APP = ApplicabilityKey(product_reference="example:health_product", policy_version="v1")
BASE = AmountPortionIdentity(kind=AmountPortionKind.BASE)


def _cell(
    *,
    timing: PersonEventTiming = PersonEventTiming.POLICY_INCEPTION,
    continuity: ContinuitySource = ContinuitySource.NONE,
    amount: AmountPortionIdentity = BASE,
    value_source: ValueSource = ValueSource.PRODUCT_RESOLVED,
    scope: WaitingPeriodScopeType = WaitingPeriodScopeType.POLICY_WIDE,
    scope_reference: str | None = None,
    wp_type: WaitingPeriodType = WaitingPeriodType.PRE_EXISTING_DISEASE,
) -> WaitingPeriodResolutionCell:
    return WaitingPeriodResolutionCell(
        applicability=APP,
        waiting_period_type=wp_type,
        scope_type=scope,
        person_event_timing=timing,
        continuity_source=continuity,
        amount_portion=amount,
        value_source=value_source,
        scope_reference=scope_reference,
    )


def _resolved():
    return compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.PRODUCT_RESOLVED,
            instance_availability=InstanceAvailability.NOT_REQUIRED,
        )
    )


def _schedule_bound():
    return compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )


def test_policy_inception_none_is_valid() -> None:
    cell = _cell()
    assert cell.person_event_timing is PersonEventTiming.POLICY_INCEPTION
    assert cell.continuity_source is ContinuitySource.NONE


def test_policy_inception_ported_is_valid() -> None:
    cell = _cell(continuity=ContinuitySource.PORTED)
    assert cell.continuity_source is ContinuitySource.PORTED


def test_member_addition_none_is_valid() -> None:
    cell = _cell(timing=PersonEventTiming.MEMBER_ADDITION)
    assert cell.person_event_timing is PersonEventTiming.MEMBER_ADDITION


def test_member_addition_ported_is_valid() -> None:
    cell = _cell(
        timing=PersonEventTiming.MEMBER_ADDITION,
        continuity=ContinuitySource.PORTED,
    )
    assert (cell.person_event_timing, cell.continuity_source) == (
        PersonEventTiming.MEMBER_ADDITION,
        ContinuitySource.PORTED,
    )


def test_member_addition_migrated_is_structurally_valid() -> None:
    cell = _cell(
        timing=PersonEventTiming.MEMBER_ADDITION,
        continuity=ContinuitySource.MIGRATED,
    )
    assert cell.continuity_source is ContinuitySource.MIGRATED


def test_unresolved_continuity_is_review_required_not_validation_conflict() -> None:
    cell = _cell(continuity=ContinuitySource.UNRESOLVED)
    resolution = continuity_resolution(cell)
    assert resolution.status is ResolutionStatus.REVIEW_REQUIRED


def test_unresolved_continuity_conservative_default_is_no_credit() -> None:
    cell = _cell(continuity=ContinuitySource.UNRESOLVED)
    assert conservative_continuity_source(cell) is ContinuitySource.NONE
    assert cell.continuity_source is ContinuitySource.UNRESOLVED


def test_migrated_continuity_requires_regulatory_verification() -> None:
    cell = _cell(continuity=ContinuitySource.MIGRATED)
    resolution = continuity_resolution(cell)
    assert resolution.status is ResolutionStatus.REGULATORY_VERIFICATION_REQUIRED


def test_base_amount_has_no_tranche_reset_anchor() -> None:
    assert BASE.effective_from is None
    assert BASE.tranche_reference is None


def test_base_amount_rejects_enhancement_fields() -> None:
    with pytest.raises(WaitingPeriodResolutionCellError):
        AmountPortionIdentity(
            kind=AmountPortionKind.BASE,
            effective_from=date(2027, 1, 1),
        )


def test_enhancement_requires_effective_date() -> None:
    with pytest.raises(WaitingPeriodResolutionCellError):
        AmountPortionIdentity(
            kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
            tranche_reference="enh_1",
        )


def test_enhancement_requires_stable_tranche_reference() -> None:
    with pytest.raises(WaitingPeriodResolutionCellError):
        AmountPortionIdentity(
            kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
            effective_from=date(2027, 1, 1),
        )


def test_two_enhancement_tranches_remain_distinct() -> None:
    first = AmountPortionIdentity(
        kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
        effective_from=date(2027, 1, 1),
        tranche_reference="enh_2027",
    )
    second = AmountPortionIdentity(
        kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
        effective_from=date(2029, 1, 1),
        tranche_reference="enh_2029",
    )
    assert first != second
    assert _cell(amount=first).dependency_identity != _cell(amount=second).dependency_identity


def test_ported_member_with_enhancement_is_valid() -> None:
    tranche = AmountPortionIdentity(
        kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
        effective_from=date(2028, 4, 1),
        tranche_reference="enh_2028_04",
    )
    cell = _cell(continuity=ContinuitySource.PORTED, amount=tranche)
    assert cell.amount_portion.kind is AmountPortionKind.ENHANCEMENT_TRANCHE


def test_newly_added_ported_member_with_enhancement_is_valid() -> None:
    tranche = AmountPortionIdentity(
        kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
        effective_from=date(2028, 4, 1),
        tranche_reference="enh_2028_04",
    )
    cell = _cell(
        timing=PersonEventTiming.MEMBER_ADDITION,
        continuity=ContinuitySource.PORTED,
        amount=tranche,
    )
    assert cell.person_event_timing is PersonEventTiming.MEMBER_ADDITION
    assert cell.continuity_source is ContinuitySource.PORTED


def test_schedule_selected_cell_is_structurally_valid_without_instance() -> None:
    cell = _cell(value_source=ValueSource.POLICY_SCHEDULE_SELECTED)
    assert cell.value_source is ValueSource.POLICY_SCHEDULE_SELECTED


def test_missing_schedule_is_resolution_state_not_invalid_cell() -> None:
    cell = _cell(value_source=ValueSource.POLICY_SCHEDULE_SELECTED)
    resolution = continuity_resolution(cell)
    assert resolution.status is ResolutionStatus.POLICY_SCHEDULE_BOUND


def test_benefit_scoped_cell_requires_reference() -> None:
    with pytest.raises(WaitingPeriodResolutionCellError):
        _cell(scope=WaitingPeriodScopeType.BENEFIT_SCOPED)


def test_benefit_scoped_cell_composes_with_axes() -> None:
    cell = _cell(
        timing=PersonEventTiming.MEMBER_ADDITION,
        continuity=ContinuitySource.PORTED,
        scope=WaitingPeriodScopeType.BENEFIT_SCOPED,
        scope_reference="doctor_prescribed_lab_radiology",
    )
    assert cell.scope_reference == "doctor_prescribed_lab_radiology"


def test_policy_wide_rejects_scope_reference() -> None:
    with pytest.raises(WaitingPeriodResolutionCellError):
        _cell(scope_reference="should_not_exist")


def test_mixed_value_sources_share_dependency_identity() -> None:
    product = _cell(value_source=ValueSource.PRODUCT_RESOLVED)
    schedule = _cell(value_source=ValueSource.POLICY_SCHEDULE_SELECTED)
    assert cells_compatible_for_dependency_join(product, schedule)
    assert product.dependency_identity == schedule.dependency_identity


def test_c2_join_mixed_value_sources_stays_resolution_gated() -> None:
    product = _cell(value_source=ValueSource.PRODUCT_RESOLVED)
    schedule = _cell(value_source=ValueSource.POLICY_SCHEDULE_SELECTED)
    result = resolve_required_inputs(
        (
            ResolutionOperand(
                "specific",
                _resolved(),
                APP,
                product.dependency_identity,
            ),
            ResolutionOperand(
                "ped",
                _schedule_bound(),
                APP,
                schedule.dependency_identity,
            ),
        )
    )
    assert result.effective_state is EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    assert result.dependency_resolution.status is ResolutionStatus.OPERAND_INSTANCE_BOUND


def test_c2_rejects_different_person_timing_cells() -> None:
    left = _cell(timing=PersonEventTiming.POLICY_INCEPTION)
    right = _cell(timing=PersonEventTiming.MEMBER_ADDITION)
    result = resolve_required_inputs(
        (
            ResolutionOperand("a", _resolved(), APP, left.dependency_identity),
            ResolutionOperand("b", _resolved(), APP, right.dependency_identity),
        )
    )
    assert result.effective_state is EffectiveDependencyState.VALIDATION_CONFLICT


def test_c2_rejects_different_continuity_cells() -> None:
    left = _cell(continuity=ContinuitySource.NONE)
    right = _cell(continuity=ContinuitySource.PORTED)
    result = resolve_required_inputs(
        (
            ResolutionOperand("a", _resolved(), APP, left.dependency_identity),
            ResolutionOperand("b", _resolved(), APP, right.dependency_identity),
        )
    )
    assert result.effective_state is EffectiveDependencyState.VALIDATION_CONFLICT


def test_c2_rejects_different_enhancement_tranches() -> None:
    first = AmountPortionIdentity(
        kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
        effective_from=date(2027, 1, 1),
        tranche_reference="enh_1",
    )
    second = AmountPortionIdentity(
        kind=AmountPortionKind.ENHANCEMENT_TRANCHE,
        effective_from=date(2029, 1, 1),
        tranche_reference="enh_2",
    )
    left = _cell(amount=first)
    right = _cell(amount=second)
    result = resolve_required_inputs(
        (
            ResolutionOperand("a", _resolved(), APP, left.dependency_identity),
            ResolutionOperand("b", _resolved(), APP, right.dependency_identity),
        )
    )
    assert result.effective_state is EffectiveDependencyState.VALIDATION_CONFLICT


def test_resolution_operand_extension_is_backward_compatible() -> None:
    operand = ResolutionOperand("legacy", _resolved(), APP)
    assert operand.resolution_cell_identity is None


def test_resolution_cell_does_not_embed_customer_amount_value() -> None:
    names = {field.name for field in fields(AmountPortionIdentity)}
    assert "amount" not in names
    assert "sum_insured" not in names


def test_resolution_cell_has_no_legacy_fused_member_basis() -> None:
    names = {field.name for field in fields(WaitingPeriodResolutionCell)}
    assert "member_waiting_basis" not in names
    assert "person_event_basis" not in names
    assert "person_event_timing" in names
    assert "continuity_source" in names


def test_amount_axis_is_separate_from_person_axis() -> None:
    names = {field.name for field in fields(WaitingPeriodResolutionCell)}
    assert "amount_portion" in names
    assert "person_event_timing" in names
    assert "continuity_source" in names


def test_no_product_specific_identity_in_c3_module() -> None:
    import inspect
    import insurance_intelligence.generic_knowledge.waiting_period_resolution_cell as module

    source = inspect.getsource(module).lower()
    assert "bajaj" not in source
    assert "star_health" not in source
    assert "aditya_birla" not in source


def test_c3_does_not_add_numeric_continuity_credit_arithmetic() -> None:
    import inspect
    import insurance_intelligence.generic_knowledge.waiting_period_resolution_cell as module

    source = inspect.getsource(module)
    assert "compute_portability_credit" not in source
    assert "compute_migration_credit" not in source
    assert "remaining_waiting_period" not in source
