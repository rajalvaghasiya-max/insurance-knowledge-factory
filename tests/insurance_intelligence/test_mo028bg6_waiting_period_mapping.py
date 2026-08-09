from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnit,
    NormativeUnitKind,
    RelationshipType,
)
from insurance_intelligence.generic_knowledge.normative_inventory import (
    NormativeInventory,
    InventoryReviewStatus,
    account_normative_inventory,
)
from insurance_intelligence.generic_knowledge.waiting_period_mapping import (
    ReviewedMappingKind,
    ReviewedWaitingPeriodMapping,
    WaitingPeriodMappingError,
    WaitingPeriodSemanticType,
    map_reviewed_waiting_period_units,
)


def _unit(unit_id: str = "norm_1") -> NormativeUnit:
    applicability = ApplicabilityKey(
        product_reference="product-x",
        optional_cover_state="BASE",
        effective_from=date(2026, 1, 1),
    )
    evidence = EvidenceReference(
        evidence_id=f"evidence_{unit_id}",
        source_document_id="doc-1",
        source_document_version="v1",
        source_hash_sha256="a" * 64,
        locator="page:1",
        authority_class="POLICY_WORDING",
    )
    return NormativeUnit(
        normative_unit_id=unit_id,
        concept="waiting_periods",
        kind=NormativeUnitKind.CONDITION,
        text_sha256="b" * 64,
        excerpt="waiting period clause",
        applicability=applicability,
        evidence=evidence,
        materially_affects=("DURATION",),
    )


def test_maps_base_mechanic_without_product_logic() -> None:
    unit = _unit()
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="human-reviewed base mechanic",
                semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                semantic_value={
                    "waiting_period_type": "PRE_EXISTING_DISEASE",
                    "duration_value": 36,
                    "duration_unit": "MONTHS",
                    "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
                    "applies_to": ["PED treatment", "direct complications"],
                },
            ),
        ),
        ontology_version="waiting-period-v1",
    )
    fact = result.semantic_facts[0]
    assert fact.value["duration_value"] == 36
    assert fact.applicability == unit.applicability
    assert fact.evidence_ids == (unit.evidence.evidence_id,)
    assert result.accounting_decisions[0].accounting_state is AccountingState.MAPPED


def test_maps_benefit_scoped_waiver_as_relationship() -> None:
    unit = _unit("norm_waiver")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.RELATIONSHIP_FACT,
                reason="benefit-specific waiver",
                relationship_type=RelationshipType.WAIVES,
                source_concept="chronic_care",
                target_concept="waiting_periods",
                relationship_condition={"waiting_period_type": "PRE_EXISTING_DISEASE"},
            ),
        ),
        ontology_version="waiting-period-v1",
    )
    relationship = result.relationship_facts[0]
    assert relationship.relationship_type is RelationshipType.WAIVES
    assert relationship.evidence_ids == (unit.evidence.evidence_id,)
    assert result.accounting_decisions[0].accounting_state is AccountingState.MAPPED_AS_RELATIONSHIP


def test_unknown_semantic_enum_fails_closed() -> None:
    unit = _unit()
    with pytest.raises(WaitingPeriodMappingError):
        map_reviewed_waiting_period_units(
            (unit,),
            (
                ReviewedWaitingPeriodMapping(
                    normative_unit_id=unit.normative_unit_id,
                    kind=ReviewedMappingKind.SEMANTIC_FACT,
                    reason="bad value",
                    semantic_type=WaitingPeriodSemanticType.DURATION,
                    semantic_value={
                        "waiting_period_type": "UNKNOWN_KIND",
                        "duration_value": 12,
                        "duration_unit": "MONTHS",
                    },
                ),
            ),
            ontology_version="waiting-period-v1",
        )


def test_not_yet_representable_becomes_blocking_residue() -> None:
    unit = _unit("norm_nyr")
    mapping_result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.NOT_YET_REPRESENTABLE,
                reason="novel suspension mechanic not supported",
            ),
        ),
        ontology_version="waiting-period-v1",
    )
    inventory = NormativeInventory(
        concept="waiting_periods",
        inventory_method="test",
        inventory_version="v1",
        review_status=InventoryReviewStatus.REVIEWED,
        units=(unit,),
    )
    accounting = account_normative_inventory(
        inventory,
        decisions=mapping_result.accounting_decisions,
        semantic_facts=mapping_result.semantic_facts,
        relationship_facts=mapping_result.relationship_facts,
    )
    assert accounting.publishable is False
    assert accounting.residues[0].accounting_state is AccountingState.NOT_YET_REPRESENTABLE


def test_missing_review_instruction_is_deferred_and_blocks() -> None:
    unit = _unit("norm_missing")
    mapping_result = map_reviewed_waiting_period_units(
        (unit,), (), ontology_version="waiting-period-v1"
    )
    assert mapping_result.accounting_decisions[0].accounting_state is AccountingState.DEFERRED_WITH_REASON


def test_schedule_dependency_is_supported_semantic_fact() -> None:
    unit = _unit("norm_schedule")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="duration delegated to schedule",
                semantic_type=WaitingPeriodSemanticType.SCHEDULE_DEPENDENCY,
                semantic_value={
                    "waiting_period_type": "PRE_EXISTING_DISEASE",
                    "detail": "duration as specified in Policy Schedule / Product Benefit Table",
                },
            ),
        ),
        ontology_version="waiting-period-v1",
    )
    assert result.semantic_facts[0].semantic_type == "SCHEDULE_DEPENDENCY"


def test_specific_disease_reduction_can_be_relationship() -> None:
    unit = _unit("norm_reduction")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.RELATIONSHIP_FACT,
                reason="optional cover modifies base waiting period",
                relationship_type=RelationshipType.MODIFIES,
                source_concept="optional_covers",
                target_concept="waiting_periods",
                relationship_condition={
                    "waiting_period_type": "SPECIFIC_DISEASE_PROCEDURE",
                    "resulting_duration_value": 1,
                    "resulting_duration_unit": "YEARS",
                },
            ),
        ),
        ontology_version="waiting-period-v1",
    )
    assert result.relationship_facts[0].relationship_type is RelationshipType.MODIFIES


def test_relationship_must_attach_to_waiting_periods() -> None:
    unit = _unit("norm_badrel")
    with pytest.raises(WaitingPeriodMappingError):
        map_reviewed_waiting_period_units(
            (unit,),
            (
                ReviewedWaitingPeriodMapping(
                    normative_unit_id=unit.normative_unit_id,
                    kind=ReviewedMappingKind.RELATIONSHIP_FACT,
                    reason="invalid unrelated edge",
                    relationship_type=RelationshipType.MODIFIES,
                    source_concept="room_rent",
                    target_concept="copayment",
                    relationship_condition={},
                ),
            ),
            ontology_version="waiting-period-v1",
        )


def test_duplicate_review_mapping_fails_closed() -> None:
    unit = _unit()
    mapping = ReviewedWaitingPeriodMapping(
        normative_unit_id=unit.normative_unit_id,
        kind=ReviewedMappingKind.EXPLICITLY_NON_APPLICABLE,
        reason="not applicable",
    )
    with pytest.raises(WaitingPeriodMappingError):
        map_reviewed_waiting_period_units(
            (unit,), (mapping, mapping), ontology_version="waiting-period-v1"
        )


def test_product_identity_is_only_carried_as_applicability_data() -> None:
    unit = _unit("norm_identity")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="generic duration mapping",
                semantic_type=WaitingPeriodSemanticType.DURATION,
                semantic_value={
                    "waiting_period_type": "INITIAL",
                    "duration_value": 30,
                    "duration_unit": "DAYS",
                },
            ),
        ),
        ontology_version="waiting-period-v1",
    )
    assert result.semantic_facts[0].applicability.product_reference == "product-x"


def test_semantic_value_validation_requires_duration_for_duration_fact() -> None:
    unit = _unit("norm_bad_duration")
    with pytest.raises(WaitingPeriodMappingError):
        map_reviewed_waiting_period_units(
            (unit,),
            (
                ReviewedWaitingPeriodMapping(
                    normative_unit_id=unit.normative_unit_id,
                    kind=ReviewedMappingKind.SEMANTIC_FACT,
                    reason="missing duration",
                    semantic_type=WaitingPeriodSemanticType.DURATION,
                    semantic_value={"waiting_period_type": "INITIAL"},
                ),
            ),
            ontology_version="waiting-period-v1",
        )
