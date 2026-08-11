from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.generic_knowledge.duration_normalization import (
    DurationNormalizationError,
    DurationUnit,
    normalize_duration,
)
from insurance_intelligence.generic_knowledge.resolution_status import ResolutionStatus
from insurance_intelligence.generic_knowledge.waiting_period_schedule_resolution import (
    BindingReviewState,
    GovernedBindingProvenance,
    InstanceDocumentClass,
    ScheduleResolutionRequest,
    ScheduleTelemetryCode,
    WaitingPeriodInstanceSelection,
    WaitingPeriodSelectionDomain,
    resolve_schedule_selection,
)


CELL = ("product:demo", "PED", "POLICY_INCEPTION", "NONE", "BASE")


def _domain(**changes) -> WaitingPeriodSelectionDomain:
    base = WaitingPeriodSelectionDomain(
        semantic_fact_id="fact_ped_duration_domain",
        resolution_cell_identity=CELL,
        allowed_values=(1, 2, 3),
        canonical_unit=DurationUnit.YEARS,
        semantic_evidence_ids=("semantic_ev_policy_wording",),
        ontology_version="health_2026_08",
        domain_version="ped_domain_v1",
    )
    return replace(base, **changes)


def _binding(**changes) -> GovernedBindingProvenance:
    base = GovernedBindingProvenance(
        binding_id="binding_schedule_ped",
        binding_method="governed_field_binding_v1",
        bound_semantic_fact_id="fact_ped_duration_domain",
        semantic_domain_version="ped_domain_v1",
        source_document_id="schedule_doc_1",
        source_document_version="v1",
        source_document_hash="schedule_hash_1",
        document_class=InstanceDocumentClass.SCHEDULE,
        review_state=BindingReviewState.APPROVED,
    )
    return replace(base, **changes)


def _selection(**changes) -> WaitingPeriodInstanceSelection:
    base = WaitingPeriodInstanceSelection(
        selection_id="selection_ped_1",
        policy_instance_reference="policy_instance_001",
        instance_document_id="schedule_doc_1",
        instance_document_version="v1",
        instance_document_hash="schedule_hash_1",
        document_class=InstanceDocumentClass.SCHEDULE,
        binding_provenance_id="binding_schedule_ped",
        semantic_fact_id="fact_ped_duration_domain",
        resolution_cell_identity=CELL,
        selected_value=3,
        selected_unit=DurationUnit.YEARS,
        instance_evidence_ids=("instance_ev_schedule_field",),
    )
    return replace(base, **changes)


def _resolve(*, domain=None, selection=None, binding=None, stale=False):
    return resolve_schedule_selection(
        ScheduleResolutionRequest(
            domain=domain or _domain(),
            selection=_selection() if selection is None else selection,
            binding=_binding() if binding is None else binding,
            instance_source_stale=stale,
        )
    )


def test_valid_schedule_selection_resolves_certified_domain() -> None:
    result = _resolve()
    assert result.resolution.status is ResolutionStatus.RESOLVED
    assert result.selected_value == 3
    assert result.selected_unit is DurationUnit.YEARS


def test_missing_schedule_remains_policy_schedule_bound() -> None:
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(domain=_domain(), selection=None, binding=None)
    )
    assert result.resolution.status is ResolutionStatus.POLICY_SCHEDULE_BOUND
    assert result.selected_value is None


@pytest.mark.parametrize(
    "document_class",
    [InstanceDocumentClass.ENDORSEMENT, InstanceDocumentClass.RIDER, InstanceDocumentClass.CERTIFICATE],
)
def test_non_schedule_document_classes_do_not_enter_value_resolution(document_class) -> None:
    selection = _selection(document_class=document_class)
    result = _resolve(selection=selection)
    assert result.resolution.status is ResolutionStatus.REVIEW_REQUIRED
    assert result.selected_value is None


def test_policy_wording_document_cannot_enter_schedule_value_path() -> None:
    result = _resolve(selection=_selection(document_class=InstanceDocumentClass.POLICY_WORDING))
    assert result.resolution.status is ResolutionStatus.REVIEW_REQUIRED


def test_missing_binding_provenance_is_review_required() -> None:
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(domain=_domain(), selection=_selection(), binding=None)
    )
    assert result.resolution.status is ResolutionStatus.REVIEW_REQUIRED


def test_unapproved_binding_is_review_required() -> None:
    result = _resolve(binding=_binding(review_state=BindingReviewState.REVIEW_REQUIRED))
    assert result.resolution.status is ResolutionStatus.REVIEW_REQUIRED


def test_forged_semantic_fact_id_cannot_bypass_binding() -> None:
    result = _resolve(selection=_selection(semantic_fact_id="fact_other"))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_binding_id_must_match_selection() -> None:
    result = _resolve(selection=_selection(binding_provenance_id="forged_binding"))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_binding_domain_version_must_match_certified_domain() -> None:
    result = _resolve(binding=_binding(semantic_domain_version="ped_domain_v0"))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_binding_document_id_must_match_selection() -> None:
    result = _resolve(binding=_binding(source_document_id="different_doc"))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_binding_document_version_must_match_selection() -> None:
    result = _resolve(binding=_binding(source_document_version="v0"))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_binding_document_hash_must_match_selection() -> None:
    result = _resolve(binding=_binding(source_document_hash="different_hash"))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_binding_document_class_must_be_schedule() -> None:
    result = _resolve(binding=_binding(document_class=InstanceDocumentClass.ENDORSEMENT))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_resolution_cell_mismatch_is_validation_conflict() -> None:
    result = _resolve(selection=_selection(resolution_cell_identity=("other", "cell")))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_out_of_domain_value_fails_closed() -> None:
    result = _resolve(selection=_selection(selected_value=4))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT
    assert result.selected_value is None


def test_out_of_domain_value_emits_domain_adequacy_telemetry() -> None:
    result = _resolve(selection=_selection(selected_value=4))
    assert len(result.telemetry) == 1
    assert result.telemetry[0].code is ScheduleTelemetryCode.DOMAIN_MEMBERSHIP_REJECTED
    assert result.telemetry[0].selected_value == 4


def test_out_of_domain_value_does_not_expand_domain() -> None:
    domain = _domain()
    _resolve(domain=domain, selection=_selection(selected_value=4))
    assert domain.allowed_values == (1, 2, 3)


def test_semantic_and_instance_evidence_remain_separate() -> None:
    result = _resolve()
    assert result.semantic_evidence_ids == ("semantic_ev_policy_wording",)
    assert result.instance_evidence_ids == ("instance_ev_schedule_field",)
    assert set(result.semantic_evidence_ids).isdisjoint(result.instance_evidence_ids)


def test_resolved_result_records_authorizing_document_class_and_binding() -> None:
    result = _resolve()
    assert result.instance_document_class is InstanceDocumentClass.SCHEDULE
    assert result.binding_provenance_id == "binding_schedule_ped"


def test_policy_instance_identity_survives_resolution() -> None:
    result = _resolve(selection=_selection(policy_instance_reference="customer_policy_A"))
    assert result.policy_instance_reference == "customer_policy_A"


def test_two_policy_instances_do_not_collapse() -> None:
    first = _resolve(selection=_selection(policy_instance_reference="policy_A"))
    second = _resolve(selection=_selection(policy_instance_reference="policy_B"))
    assert first.policy_instance_reference != second.policy_instance_reference
    assert first.resolution_cell_identity == second.resolution_cell_identity


def test_instance_document_identity_survives_resolution() -> None:
    result = _resolve()
    assert result.instance_document_id == "schedule_doc_1"
    assert result.instance_document_version == "v1"
    assert result.instance_document_hash == "schedule_hash_1"


def test_known_stale_instance_source_degrades_to_source_stale() -> None:
    result = _resolve(stale=True)
    assert result.resolution.status is ResolutionStatus.SOURCE_STALE
    assert result.selected_value is None


def test_exact_years_to_months_normalization_is_supported() -> None:
    result = normalize_duration(2, DurationUnit.YEARS, DurationUnit.MONTHS)
    assert result.value == 24
    assert result.unit is DurationUnit.MONTHS


def test_exact_months_to_years_normalization_is_supported() -> None:
    result = normalize_duration(24, DurationUnit.MONTHS, DurationUnit.YEARS)
    assert result.value == 2
    assert result.unit is DurationUnit.YEARS


def test_fractional_months_to_years_is_refused() -> None:
    with pytest.raises(DurationNormalizationError):
        normalize_duration(25, DurationUnit.MONTHS, DurationUnit.YEARS)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (DurationUnit.YEARS, DurationUnit.DAYS),
        (DurationUnit.MONTHS, DurationUnit.DAYS),
        (DurationUnit.DAYS, DurationUnit.MONTHS),
        (DurationUnit.DAYS, DurationUnit.YEARS),
    ],
)
def test_calendar_day_count_conversions_are_refused(source, target) -> None:
    with pytest.raises(DurationNormalizationError):
        normalize_duration(2, source, target)


def test_equivalent_schedule_unit_can_resolve_against_canonical_domain() -> None:
    domain = _domain(allowed_values=(2,), canonical_unit=DurationUnit.YEARS)
    result = _resolve(domain=domain, selection=_selection(selected_value=24, selected_unit=DurationUnit.MONTHS))
    assert result.resolution.status is ResolutionStatus.RESOLVED
    assert result.selected_value == 2
    assert result.selected_unit is DurationUnit.YEARS


def test_unsupported_unit_conversion_is_validation_conflict_not_guess() -> None:
    result = _resolve(selection=_selection(selected_value=730, selected_unit=DurationUnit.DAYS))
    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_schedule_selection_cannot_author_resolution_status() -> None:
    assert "resolution" not in WaitingPeriodInstanceSelection.__dataclass_fields__


def test_domain_contract_owns_semantic_evidence() -> None:
    assert "semantic_evidence_ids" in WaitingPeriodSelectionDomain.__dataclass_fields__
    assert "semantic_evidence_ids" not in WaitingPeriodInstanceSelection.__dataclass_fields__


def test_instance_selection_owns_instance_evidence_only() -> None:
    assert "instance_evidence_ids" in WaitingPeriodInstanceSelection.__dataclass_fields__


def test_no_implicit_multi_cell_projection_field_exists() -> None:
    assert "projection_cells" not in WaitingPeriodInstanceSelection.__dataclass_fields__
    assert "projection_cells" not in WaitingPeriodSelectionDomain.__dataclass_fields__


def test_c4_contract_has_no_free_text_schedule_parser_surface() -> None:
    fields = set(WaitingPeriodInstanceSelection.__dataclass_fields__)
    assert "schedule_text" not in fields
    assert "raw_text" not in fields
    assert "prompt" not in fields


def test_c4_result_does_not_contain_expiry_or_remaining_wait_fields() -> None:
    result = _resolve()
    fields = set(result.__dataclass_fields__)
    assert "expiry_date" not in fields
    assert "remaining_wait" not in fields
    assert "longer_of" not in fields
