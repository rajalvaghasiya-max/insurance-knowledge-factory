import pytest

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodContractError,
    WaitingPeriodDurationUnit,
    WaitingPeriodScopeType,
    WaitingPeriodType,
    WaitingPeriodValueSource,
)
from insurance_intelligence.benefits.waiting_period_option_domain import (
    WaitingPeriodDurationOption,
    WaitingPeriodDurationOptionDomain,
)


def _options():
    return tuple(
        WaitingPeriodDurationOption(value, WaitingPeriodDurationUnit.YEARS)
        for value in (1, 2, 3)
    )


def _domain(**overrides):
    values = dict(
        waiting_period_type=WaitingPeriodType.PRE_EXISTING_DISEASE,
        options=_options(),
        applies_to=("pre_existing_disease",),
        evidence_reference_ids=("policy_wording:candidate_page_53:sha",),
        schedule_dependency="Policy Schedule selects one of the documented options.",
    )
    values.update(overrides)
    return WaitingPeriodDurationOptionDomain(**values)


def test_preserves_ordered_schedule_selected_duration_options_without_resolving_one():
    domain = _domain()
    assert tuple(item.duration_value for item in domain.options) == (1, 2, 3)
    assert domain.value_source is WaitingPeriodValueSource.POLICY_SCHEDULE_SELECTED
    assert "selected" not in domain.__dataclass_fields__
    assert "duration_value" not in domain.__dataclass_fields__


def test_requires_at_least_two_options():
    with pytest.raises(WaitingPeriodContractError, match="at least two"):
        _domain(options=(WaitingPeriodDurationOption(1, WaitingPeriodDurationUnit.YEARS),))


def test_rejects_duplicate_options():
    with pytest.raises(WaitingPeriodContractError, match="duplicates"):
        option = WaitingPeriodDurationOption(1, WaitingPeriodDurationUnit.YEARS)
        _domain(options=(option, option))


def test_requires_deterministic_ascending_order():
    with pytest.raises(WaitingPeriodContractError, match="ascending"):
        _domain(options=tuple(reversed(_options())))


def test_rejects_mixed_duration_units():
    with pytest.raises(WaitingPeriodContractError, match="common duration unit"):
        _domain(
            options=(
                WaitingPeriodDurationOption(12, WaitingPeriodDurationUnit.MONTHS),
                WaitingPeriodDurationOption(2, WaitingPeriodDurationUnit.YEARS),
            )
        )


def test_requires_evidence_and_schedule_dependency():
    with pytest.raises(WaitingPeriodContractError, match="requires evidence"):
        _domain(evidence_reference_ids=())
    with pytest.raises(WaitingPeriodContractError, match="schedule_dependency"):
        _domain(schedule_dependency="")


def test_unresolved_domain_cannot_claim_product_fixed_value_source():
    with pytest.raises(WaitingPeriodContractError, match="POLICY_SCHEDULE_SELECTED"):
        _domain(value_source=WaitingPeriodValueSource.PRODUCT_FIXED)


def test_benefit_scoped_domain_requires_reference():
    with pytest.raises(WaitingPeriodContractError, match="scope_reference"):
        _domain(scope_type=WaitingPeriodScopeType.BENEFIT_SCOPED)
