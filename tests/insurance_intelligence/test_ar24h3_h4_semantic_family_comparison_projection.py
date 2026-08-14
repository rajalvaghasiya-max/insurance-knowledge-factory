from insurance_intelligence.generic_knowledge.benefit_limit_applicability import (
    BenefitLimitApplicability,
    BenefitLimitApplicabilityCell,
)
from insurance_intelligence.generic_knowledge.benefit_limit_comparison_projection import (
    project_benefit_limit_dimension,
)
from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    BenefitIdentityReference,
    BenefitLimitMechanic,
    CostSharingApplicability,
    CostSharingInteractionRule,
    CostSharingMechanicType,
    CostSharingOrdering,
    EventScope,
    LimitKind,
    MonetaryAmount,
    TimeScope,
)
from insurance_intelligence.generic_knowledge.comparison_projection import (
    ComparableDimension,
    NotApplicableDimension,
    NotComparableDimension,
    NotComparableReasonCode,
)
from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    EvidenceReference,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    ResolutionInputs,
    ValueSource,
    compute_resolution_status,
)
from insurance_intelligence.generic_knowledge.waiting_period_comparison_projection import (
    project_waiting_period_dimension,
)


def _app(product: str = "pv_test") -> ApplicabilityKey:
    return ApplicabilityKey(product_reference=product, policy_version="v1")


def _evidence(evidence_id: str) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id=f"doc_{evidence_id}",
        source_document_version="v1",
        source_hash_sha256=f"sha_{evidence_id}",
        locator="page:1",
        authority_class="POLICY_WORDING",
    )


def _benefit_cell(*, ordering: CostSharingOrdering) -> BenefitLimitApplicabilityCell:
    core = _evidence("core")
    scope = _evidence("scope")
    interaction = _evidence("interaction")
    mechanic = BenefitLimitMechanic(
        benefit_identity=BenefitIdentityReference(
            concept_id="health:benefit:cataract",
            alias_registry_version="v1",
            alias_registry_snapshot_id="snapshot-1",
        ),
        limit_kind=LimitKind.FIXED_CURRENCY,
        ontology_version="benefit-limit-v1",
        core_evidence_references=(core,),
        amount=MonetaryAmount(40000),
        time_scope=TimeScope.PER_POLICY_YEAR,
        event_scope=EventScope.PER_CLAIM,
        scope_evidence_references=(scope,),
        cost_sharing_interactions=(
            CostSharingInteractionRule(
                mechanic_type=CostSharingMechanicType.COPAY,
                applies=CostSharingApplicability.YES,
                ordering=ordering,
                evidence_references=(interaction,),
            ),
        ),
    )
    return BenefitLimitApplicabilityCell(
        mechanic=mechanic,
        applicability=BenefitLimitApplicability(base_applicability=_app()),
    )


def test_waiting_period_resolved_mapped_dimension_is_comparable() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED)
    )
    result = project_waiting_period_dimension(
        concept_id="health:waiting_period:ped",
        dimension_id="ped_duration",
        applicability=_app(),
        evidence_ids=("e1",),
        accounting_state=AccountingState.MAPPED,
        resolution=resolution,
        structured_value={"duration": 36, "unit": "MONTHS"},
    )
    assert type(result) is ComparableDimension
    assert result.structured_value["duration"] == 36


def test_waiting_period_policy_schedule_bound_is_not_comparable_not_absent() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    result = project_waiting_period_dimension(
        concept_id="health:waiting_period:ped",
        dimension_id="ped_duration",
        applicability=_app(),
        evidence_ids=("e1",),
        accounting_state=AccountingState.MAPPED,
        resolution=resolution,
        structured_value={"duration_source": "POLICY_SCHEDULE"},
    )
    assert type(result) is NotComparableDimension
    assert result.reason_code is NotComparableReasonCode.RESOLUTION_BLOCKED
    assert result.producer_state == "POLICY_SCHEDULE_BOUND"
    assert not hasattr(result, "structured_value")


def test_waiting_period_material_residue_blocks_even_resolved_mapping() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED)
    )
    result = project_waiting_period_dimension(
        concept_id="health:waiting_period:ped",
        dimension_id="ped_duration",
        applicability=_app(),
        evidence_ids=("e1",),
        accounting_state=AccountingState.MAPPED,
        resolution=resolution,
        structured_value={"duration": 36, "unit": "MONTHS"},
        material_residue_reasons=("material exception remains unresolved",),
    )
    assert type(result) is NotComparableDimension
    assert result.reason_code is NotComparableReasonCode.MATERIAL_RESIDUE


def test_explicit_non_applicability_is_distinct_from_unresolved_waiting_period() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED)
    )
    result = project_waiting_period_dimension(
        concept_id="health:waiting_period:ped",
        dimension_id="ped_duration",
        applicability=_app(),
        evidence_ids=("e1",),
        accounting_state=AccountingState.EXPLICITLY_NON_APPLICABLE,
        resolution=resolution,
        structured_value=None,
    )
    assert type(result) is NotApplicableDimension


def test_benefit_limit_comparison_ready_mechanic_projects_complete_value() -> None:
    cell = _benefit_cell(ordering=CostSharingOrdering.AFTER_LIMIT)
    assert cell.mechanic.equivalence_ready is True
    result = project_benefit_limit_dimension(
        cell=cell,
        dimension_id="cataract_limit",
        evidence_ids=("core", "scope", "interaction"),
        accounting_state=AccountingState.MAPPED,
    )
    assert type(result) is ComparableDimension
    assert result.structured_value["amount"]["amount"] == 40000.0
    assert result.structured_value["cost_sharing_interactions"] == (
        {"mechanic_type": "COPAY", "applies": "YES", "ordering": "AFTER_LIMIT"},
    )


def test_benefit_limit_unknown_interaction_ordering_is_not_comparable() -> None:
    cell = _benefit_cell(ordering=CostSharingOrdering.UNKNOWN)
    assert cell.mechanic.equivalence_ready is False
    result = project_benefit_limit_dimension(
        cell=cell,
        dimension_id="cataract_limit",
        evidence_ids=("core", "scope", "interaction"),
        accounting_state=AccountingState.MAPPED,
    )
    assert type(result) is NotComparableDimension
    assert result.reason_code is NotComparableReasonCode.COMPARISON_READINESS_BLOCKED
    assert result.producer_state == "EQUIVALENCE_NOT_READY"
    assert not hasattr(result, "structured_value")


def test_benefit_limit_material_residue_blocks_equivalence_ready_mechanic() -> None:
    cell = _benefit_cell(ordering=CostSharingOrdering.AFTER_LIMIT)
    result = project_benefit_limit_dimension(
        cell=cell,
        dimension_id="cataract_limit",
        evidence_ids=("core", "scope", "interaction"),
        accounting_state=AccountingState.MAPPED,
        material_residue_reasons=("shared aggregate relationship remains unresolved",),
    )
    assert type(result) is NotComparableDimension
    assert result.reason_code is NotComparableReasonCode.MATERIAL_RESIDUE


def test_explicit_non_applicability_is_distinct_from_unresolved_benefit_limit() -> None:
    cell = _benefit_cell(ordering=CostSharingOrdering.AFTER_LIMIT)
    result = project_benefit_limit_dimension(
        cell=cell,
        dimension_id="cataract_limit",
        evidence_ids=("core",),
        accounting_state=AccountingState.EXPLICITLY_NON_APPLICABLE,
    )
    assert type(result) is NotApplicableDimension
