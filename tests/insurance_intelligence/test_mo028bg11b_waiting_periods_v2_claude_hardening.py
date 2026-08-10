from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodMemberBasis,
    WaitingPeriodScopeType,
    WaitingPeriodValueSource,
)
from insurance_intelligence.concepts.waiting_periods.policy import (
    waiting_period_concept_policy,
    waiting_period_concept_policy_v2,
)
from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnit,
    NormativeUnitKind,
    RelationshipType,
)
from insurance_intelligence.generic_knowledge.semantic_core import (
    HEALTH_WAITING_PERIOD_TYPE_IDS,
    HEALTH_WAITING_PERIODS,
    HEALTH_WAITING_PERIODS_V2,
)
from insurance_intelligence.generic_knowledge.waiting_period_mapping import (
    ReviewedMappingKind,
    ReviewedWaitingPeriodMapping,
    WaitingPeriodMappingError,
    WaitingPeriodSemanticType,
    map_reviewed_waiting_period_units,
)
from insurance_intelligence.generic_knowledge.waiting_period_migration import (
    migrate_waiting_period_record,
)


def _unit(unit_id: str) -> NormativeUnit:
    applicability = ApplicabilityKey(
        product_reference="product://g11-v2-hardening",
        policy_version="v1",
        effective_from=date(2026, 1, 1),
    )
    evidence = EvidenceReference(
        evidence_id=f"evidence_{unit_id}",
        source_document_id="doc-g11",
        source_document_version="doc-v1",
        source_hash_sha256="a" * 64,
        locator=f"page:{unit_id}",
        authority_class="POLICY_WORDING",
    )
    return NormativeUnit(
        normative_unit_id=unit_id,
        concept="waiting_periods",
        kind=NormativeUnitKind.CONDITION,
        text_sha256="b" * 64,
        excerpt="governed waiting-period clause",
        applicability=applicability,
        evidence=evidence,
        materially_affects=("DURATION", "APPLICABILITY"),
    )


def _map(unit: NormativeUnit, mapping: ReviewedWaitingPeriodMapping):
    return map_reviewed_waiting_period_units(
        (unit,),
        (mapping,),
        ontology_version="waiting_periods_v2",
    )


def test_v2_preserves_canonical_concept_identity_and_bumps_semantic_version():
    assert HEALTH_WAITING_PERIODS.canonical_id == HEALTH_WAITING_PERIODS_V2.canonical_id
    assert HEALTH_WAITING_PERIODS.concept_semantic_version == "1"
    assert HEALTH_WAITING_PERIODS_V2.concept_semantic_version == "2"
    assert HEALTH_WAITING_PERIODS_V2.fact_schema_id == "waiting_periods_v2"


def test_new_waiting_period_types_have_stable_health_namespaced_ids():
    assert HEALTH_WAITING_PERIOD_TYPE_IDS["MATERNITY"] == "health.waiting_period.maternity"
    assert HEALTH_WAITING_PERIOD_TYPE_IDS["BABY_CARE"] == "health.waiting_period.baby_care"
    assert len(set(HEALTH_WAITING_PERIOD_TYPE_IDS.values())) == len(HEALTH_WAITING_PERIOD_TYPE_IDS)


def test_derives_from_is_additive_to_v2_not_backported_into_v1_policy():
    assert RelationshipType.DERIVES_FROM not in waiting_period_concept_policy().allowed_relationship_types
    assert RelationshipType.DERIVES_FROM in waiting_period_concept_policy_v2().allowed_relationship_types


def test_schedule_selected_duration_publishes_option_domain_not_invented_scalar():
    unit = _unit("selection")
    result = _map(
        unit,
        ReviewedWaitingPeriodMapping(
            normative_unit_id=unit.normative_unit_id,
            kind=ReviewedMappingKind.SEMANTIC_FACT,
            reason="schedule carries selected PED duration",
            semantic_type=WaitingPeriodSemanticType.DURATION_SELECTION,
            semantic_value={
                "waiting_period_type": "PRE_EXISTING_DISEASE",
                "duration_options": [
                    {"duration_value": 1, "duration_unit": "YEARS"},
                    {"duration_value": 2, "duration_unit": "YEARS"},
                    {"duration_value": 3, "duration_unit": "YEARS"},
                ],
                "value_source": "POLICY_SCHEDULE_SELECTED",
                "resolved_value_status": "POLICY_SCHEDULE_BOUND",
            },
        ),
    )
    value = result.semantic_facts[0].value
    assert value["value_source"] == WaitingPeriodValueSource.POLICY_SCHEDULE_SELECTED.value
    assert value["resolved_value_status"] == "POLICY_SCHEDULE_BOUND"
    assert "duration_value" not in value
    assert len(value["duration_options"]) == 3


def test_schedule_selected_duration_rejects_product_fixed_or_fake_resolution():
    unit = _unit("bad_selection")
    with pytest.raises(WaitingPeriodMappingError):
        _map(
            unit,
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="must remain unresolved without policy schedule",
                semantic_type=WaitingPeriodSemanticType.DURATION_SELECTION,
                semantic_value={
                    "waiting_period_type": "PRE_EXISTING_DISEASE",
                    "duration_options": [{"duration_value": 3, "duration_unit": "YEARS"}],
                    "value_source": "PRODUCT_FIXED",
                    "resolved_value_status": "RESOLVED",
                },
            ),
        )


def test_same_waiting_period_type_can_exist_policy_wide_and_benefit_scoped():
    policy_unit = _unit("policy_ped")
    benefit_unit = _unit("benefit_ped")
    result = map_reviewed_waiting_period_units(
        (policy_unit, benefit_unit),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=policy_unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="policy-wide PED",
                semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                semantic_value={
                    "waiting_period_type": "PRE_EXISTING_DISEASE",
                    "duration_value": 36,
                    "duration_unit": "MONTHS",
                    "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
                    "applies_to": ["PED treatment"],
                    "scope_type": "POLICY_WIDE",
                },
            ),
            ReviewedWaitingPeriodMapping(
                normative_unit_id=benefit_unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="benefit-scoped PED",
                semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                semantic_value={
                    "waiting_period_type": "PRE_EXISTING_DISEASE",
                    "duration_value": 24,
                    "duration_unit": "MONTHS",
                    "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
                    "applies_to": ["investigation benefit"],
                    "scope_type": "BENEFIT_SCOPED",
                    "scope_reference": "benefit:investigation_cover",
                },
            ),
        ),
        ontology_version="waiting_periods_v2",
    )
    assert len(result.semantic_facts) == 2
    scopes = {(fact.value["scope_type"], fact.value.get("scope_reference")) for fact in result.semantic_facts}
    assert scopes == {
        (WaitingPeriodScopeType.POLICY_WIDE.value, None),
        (WaitingPeriodScopeType.BENEFIT_SCOPED.value, "benefit:investigation_cover"),
    }


def test_benefit_scoped_fact_fails_closed_without_scope_reference():
    unit = _unit("missing_scope")
    with pytest.raises(WaitingPeriodMappingError):
        _map(
            unit,
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="benefit scope must be explicit",
                semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                semantic_value={
                    "waiting_period_type": "INITIAL",
                    "duration_value": 30,
                    "duration_unit": "DAYS",
                    "start_basis": "POLICY_INCEPTION",
                    "applies_to": ["benefit"],
                    "scope_type": "BENEFIT_SCOPED",
                },
            ),
        )


def test_new_member_reset_is_explicit_member_addition_event():
    unit = _unit("new_member")
    result = _map(
        unit,
        ReviewedWaitingPeriodMapping(
            normative_unit_id=unit.normative_unit_id,
            kind=ReviewedMappingKind.SEMANTIC_FACT,
            reason="freshly added insured starts waits afresh",
            semantic_type=WaitingPeriodSemanticType.NEW_MEMBER_EFFECT,
            semantic_value={
                "waiting_period_type": "PRE_EXISTING_DISEASE",
                "start_basis": "INSURED_PERSON_ADDITION_DATE",
                "member_waiting_basis": "MEMBER_ADDITION",
                "detail": "waiting periods apply afresh for newly added insured member",
            },
        ),
    )
    assert result.semantic_facts[0].value["member_waiting_basis"] == WaitingPeriodMemberBasis.MEMBER_ADDITION.value


def test_portability_continuity_is_sibling_event_not_new_member_reset():
    unit = _unit("portability")
    result = _map(
        unit,
        ReviewedWaitingPeriodMapping(
            normative_unit_id=unit.normative_unit_id,
            kind=ReviewedMappingKind.SEMANTIC_FACT,
            reason="ported member preserves accrued continuity",
            semantic_type=WaitingPeriodSemanticType.PORTABILITY,
            semantic_value={
                "waiting_period_type": "PRE_EXISTING_DISEASE",
                "member_waiting_basis": "PORTED_CONTINUITY",
                "detail": "accrued continuity benefits in waiting periods are preserved",
            },
        ),
    )
    assert result.semantic_facts[0].value["member_waiting_basis"] == WaitingPeriodMemberBasis.PORTED_CONTINUITY.value


def test_day_care_inherited_wait_can_be_governed_derives_from_relationship():
    unit = _unit("daycare")
    result = _map(
        unit,
        ReviewedWaitingPeriodMapping(
            normative_unit_id=unit.normative_unit_id,
            kind=ReviewedMappingKind.RELATIONSHIP_FACT,
            reason="day-care wait follows underlying disease/condition",
            relationship_type=RelationshipType.DERIVES_FROM,
            source_concept="day_care_coverage",
            target_concept="waiting_periods",
            relationship_condition={"resolution_basis": "underlying_medical_condition"},
        ),
    )
    assert result.relationship_facts[0].relationship_type is RelationshipType.DERIVES_FROM


def test_generic_migration_loader_passes_relationship_fact_fields_without_product_branch():
    record = {
        "record_type": "generic_waiting_period_migration_v1",
        "product_reference": "product://synthetic",
        "policy_version": "v1",
        "ontology_version": "waiting_periods_v2",
        "review_decision_version": "review-v1",
        "inventory_version": "inventory-v1",
        "source": {
            "document_id": "doc-synthetic",
            "document_version": "doc-v1",
            "sha256": "c" * 64,
            "authority_class": "POLICY_WORDING",
        },
        "units": [
            {
                "unit_id": "rel_unit",
                "locator": "page:1",
                "evidence_id": "evidence-rel",
                "materially_affects": ["CROSS_CONCEPT_RELATIONSHIP"],
                "kind": "RELATIONSHIP",
                "text_sha256": "d" * 64,
                "excerpt": "inherited wait",
                "reviewed_mapping": {
                    "kind": "RELATIONSHIP_FACT",
                    "reason": "reviewed inherited-wait relationship",
                    "relationship_type": "DERIVES_FROM",
                    "source_concept": "day_care_coverage",
                    "target_concept": "waiting_periods",
                    "relationship_condition": {"resolution_basis": "underlying_condition"},
                },
            }
        ],
    }
    result = migrate_waiting_period_record(record)
    assert result.accounting.publishable
    assert result.accounting.telemetry.residue_count == 0
    assert result.mapping.relationship_facts[0].relationship_type is RelationshipType.DERIVES_FROM


def test_long_term_upfront_reduction_reuses_modifies_relationship_not_new_type():
    unit = _unit("maternity_reduce")
    result = _map(
        unit,
        ReviewedWaitingPeriodMapping(
            normative_unit_id=unit.normative_unit_id,
            kind=ReviewedMappingKind.RELATIONSHIP_FACT,
            reason="upfront long-term premium reduces maternity wait by one year",
            relationship_type=RelationshipType.MODIFIES,
            source_concept="premium_payment_configuration",
            target_concept="waiting_periods",
            relationship_condition={
                "waiting_period_type": "MATERNITY",
                "policy_tenure": "LONG_TERM",
                "payment_mode": "UPFRONT",
                "reduction_value": 1,
                "reduction_unit": "YEARS",
            },
        ),
    )
    assert result.relationship_facts[0].relationship_type is RelationshipType.MODIFIES
