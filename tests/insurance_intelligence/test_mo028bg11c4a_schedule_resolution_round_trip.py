from __future__ import annotations

from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey
from insurance_intelligence.generic_knowledge.dependency_resolution import (
    EffectiveDependencyState,
    ResolutionOperand,
    resolve_required_inputs,
)
from insurance_intelligence.generic_knowledge.duration_normalization import DurationUnit
from insurance_intelligence.generic_knowledge.resolution_status import (
    ComputedResolution,
    ResolutionSeverity,
    ResolutionStatus,
)
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


APP = ApplicabilityKey(product_reference="synthetic_health:plan_a")
CELL = ("PED", "POLICY_WIDE", "POLICY_INCEPTION", "NONE", "BASE")


def _domain() -> WaitingPeriodSelectionDomain:
    return WaitingPeriodSelectionDomain(
        semantic_fact_id="fact_ped_duration_domain",
        resolution_cell_identity=CELL,
        allowed_values=(1, 2, 3),
        canonical_unit=DurationUnit.YEARS,
        semantic_evidence_ids=("evidence_policy_wording_ped_domain",),
        ontology_version="health_waiting_periods_v2",
        domain_version="ped_domain_v1",
    )


def _binding() -> GovernedBindingProvenance:
    return GovernedBindingProvenance(
        binding_id="binding_schedule_ped_v1",
        binding_method="governed_fixture_binding",
        bound_semantic_fact_id="fact_ped_duration_domain",
        semantic_domain_version="ped_domain_v1",
        source_document_id="schedule_doc_001",
        source_document_version="v1",
        source_document_hash="schedule_hash_001",
        document_class=InstanceDocumentClass.SCHEDULE,
        review_state=BindingReviewState.APPROVED,
    )


def _selection(value: int) -> WaitingPeriodInstanceSelection:
    return WaitingPeriodInstanceSelection(
        selection_id=f"selection_ped_{value}",
        policy_instance_reference="policy_instance_customer_001",
        instance_document_id="schedule_doc_001",
        instance_document_version="v1",
        instance_document_hash="schedule_hash_001",
        document_class=InstanceDocumentClass.SCHEDULE,
        binding_provenance_id="binding_schedule_ped_v1",
        semantic_fact_id="fact_ped_duration_domain",
        resolution_cell_identity=CELL,
        selected_value=value,
        selected_unit=DurationUnit.YEARS,
        instance_evidence_ids=("evidence_schedule_ped_selection",),
    )


def _resolved_specific_operand() -> ResolutionOperand:
    return ResolutionOperand(
        operand_id="specific_wait",
        resolution=ComputedResolution(
            status=ResolutionStatus.RESOLVED,
            severity=ResolutionSeverity.RESOLVED,
        ),
        applicability=APP,
        resolution_cell_identity=CELL,
    )


def test_c4a_positive_round_trip_resolves_authenticated_schedule_value() -> None:
    domain = _domain()
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(
            domain=domain,
            selection=_selection(3),
            binding=_binding(),
        )
    )

    assert result.resolution.status is ResolutionStatus.RESOLVED
    assert result.selected_value == 3
    assert result.selected_unit is DurationUnit.YEARS
    assert result.resolution_cell_identity == CELL
    assert result.policy_instance_reference == "policy_instance_customer_001"
    assert result.semantic_evidence_ids == ("evidence_policy_wording_ped_domain",)
    assert result.instance_evidence_ids == ("evidence_schedule_ped_selection",)
    assert result.instance_document_class is InstanceDocumentClass.SCHEDULE
    assert result.binding_provenance_id == "binding_schedule_ped_v1"


def test_c4a_resolved_value_becomes_eligible_for_c2_required_input_consumption() -> None:
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(
            domain=_domain(),
            selection=_selection(3),
            binding=_binding(),
        )
    )
    ped_operand = ResolutionOperand(
        operand_id="ped_wait",
        resolution=result.resolution,
        applicability=APP,
        resolution_cell_identity=result.resolution_cell_identity,
    )

    downstream = resolve_required_inputs((ped_operand, _resolved_specific_operand()))

    assert downstream.effective_state is EffectiveDependencyState.FULLY_RESOLVED
    assert downstream.dependency_resolution is not None
    assert downstream.dependency_resolution.status is ResolutionStatus.RESOLVED


def test_c4a_missing_schedule_remains_unresolved_and_blocks_c2_consumption() -> None:
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(domain=_domain(), selection=None, binding=None)
    )
    ped_operand = ResolutionOperand(
        operand_id="ped_wait",
        resolution=result.resolution,
        applicability=APP,
        resolution_cell_identity=CELL,
    )

    downstream = resolve_required_inputs((ped_operand, _resolved_specific_operand()))

    assert result.resolution.status is ResolutionStatus.POLICY_SCHEDULE_BOUND
    assert downstream.effective_state is EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    assert downstream.dependency_resolution is not None
    assert downstream.dependency_resolution.status is ResolutionStatus.OPERAND_INSTANCE_BOUND


def test_c4a_out_of_domain_selection_is_rejected_and_emits_domain_telemetry() -> None:
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(
            domain=_domain(),
            selection=_selection(4),
            binding=_binding(),
        )
    )

    assert result.resolution.status is ResolutionStatus.VALIDATION_CONFLICT
    assert result.selected_value is None
    assert result.selected_unit is None
    assert len(result.telemetry) == 1
    assert result.telemetry[0].code is ScheduleTelemetryCode.DOMAIN_MEMBERSHIP_REJECTED


def test_c4a_out_of_domain_value_never_becomes_usable_downstream() -> None:
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(
            domain=_domain(),
            selection=_selection(4),
            binding=_binding(),
        )
    )
    ped_operand = ResolutionOperand(
        operand_id="ped_wait",
        resolution=result.resolution,
        applicability=APP,
        resolution_cell_identity=CELL,
    )

    downstream = resolve_required_inputs((ped_operand, _resolved_specific_operand()))

    assert downstream.effective_state is EffectiveDependencyState.VALIDATION_CONFLICT
    assert downstream.dependency_resolution is not None
    assert downstream.dependency_resolution.status is ResolutionStatus.VALIDATION_CONFLICT


def test_c4a_round_trip_does_not_compute_longer_of_value() -> None:
    result = resolve_schedule_selection(
        ScheduleResolutionRequest(
            domain=_domain(),
            selection=_selection(3),
            binding=_binding(),
        )
    )

    assert result.selected_value == 3
    assert not hasattr(result, "longer_of_value")
    assert not hasattr(result, "effective_waiting_period")
