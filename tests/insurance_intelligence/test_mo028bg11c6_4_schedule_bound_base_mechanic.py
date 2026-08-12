from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnit,
    NormativeUnitKind,
)
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    PublicationDependencyBinding,
    dependency_binding_matches,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    ResolutionInputs,
    ResolutionStatus,
    ValueSource,
    compute_resolution_status,
)
from insurance_intelligence.generic_knowledge.waiting_period_duration_domain import (
    DurationDomainDependencyBinding,
)
from insurance_intelligence.generic_knowledge.waiting_period_mapping import (
    ReviewedMappingKind,
    ReviewedWaitingPeriodMapping,
    WaitingPeriodMappingError,
    WaitingPeriodSemanticType,
    map_reviewed_waiting_period_units,
)


ARTIFACT = Path(
    "docs/architecture/MO_028B_G11_C6_4_BAJAJ_SCHEDULE_BOUND_BASE_MECHANIC_ADJUDICATION.json"
)


def _unit(unit_id: str, *, applicability: ApplicabilityKey | None = None) -> NormativeUnit:
    applicability = applicability or ApplicabilityKey(product_reference="product://generic")
    return NormativeUnit(
        normative_unit_id=unit_id,
        concept="waiting_periods",
        kind=NormativeUnitKind.CONDITION,
        text_sha256=(unit_id[0] if unit_id else "a") * 64,
        excerpt=f"governed source proposition for {unit_id}",
        applicability=applicability,
        evidence=EvidenceReference(
            evidence_id=f"evidence_{unit_id}",
            source_document_id="policy_wording",
            source_document_version="v1",
            source_hash_sha256="a" * 64,
            locator=f"page:{unit_id}",
            authority_class="POLICY_WORDING",
        ),
        materially_affects=("DURATION", "APPLICABILITY"),
    )


def _domain_mapping(
    unit_id: str = "domain",
    *,
    waiting_period_type: str = "SPECIFIC_DISEASE_PROCEDURE",
    scope_type: str = "POLICY_WIDE",
    scope_reference: str | None = None,
) -> ReviewedWaitingPeriodMapping:
    value: dict[str, object] = {
        "waiting_period_type": waiting_period_type,
        "duration_options": [
            {"duration_value": 1, "duration_unit": "YEARS"},
            {"duration_value": 2, "duration_unit": "YEARS"},
            {"duration_value": 3, "duration_unit": "YEARS"},
        ],
        "selection_basis": "Policy Schedule",
        "value_source": "POLICY_SCHEDULE_SELECTED",
        "resolved_value_status": "POLICY_SCHEDULE_BOUND",
        "scope_type": scope_type,
    }
    if scope_reference is not None:
        value["scope_reference"] = scope_reference
    return ReviewedWaitingPeriodMapping(
        normative_unit_id=unit_id,
        kind=ReviewedMappingKind.SEMANTIC_FACT,
        reason="governed schedule-selected duration domain",
        semantic_type=WaitingPeriodSemanticType.DURATION_SELECTION,
        semantic_value=value,
    )


def _base_mapping(
    *,
    reference_fact_id: str = "fact_domain_duration_selection",
    reference_type: str = "SPECIFIC_DISEASE_PROCEDURE",
    reference_ontology: str = "waiting_periods_v2",
    scope_type: str = "POLICY_WIDE",
    scope_reference: str | None = None,
) -> ReviewedWaitingPeriodMapping:
    value: dict[str, object] = {
        "waiting_period_type": "SPECIFIC_DISEASE_PROCEDURE",
        "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
        "applies_to": ["specified diseases and procedures"],
        "scope_type": scope_type,
        "duration_domain_reference": {
            "semantic_fact_id": reference_fact_id,
            "waiting_period_type": reference_type,
            "ontology_version": reference_ontology,
        },
    }
    if scope_reference is not None:
        value["scope_reference"] = scope_reference
    return ReviewedWaitingPeriodMapping(
        normative_unit_id="base",
        kind=ReviewedMappingKind.SEMANTIC_FACT,
        reason="base mechanic delegates duration to governed schedule domain",
        semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
        semantic_value=value,
    )


def _map_pair(
    base_mapping: ReviewedWaitingPeriodMapping | None = None,
    domain_mapping: ReviewedWaitingPeriodMapping | None = None,
):
    applicability = ApplicabilityKey(product_reference="product://generic")
    return map_reviewed_waiting_period_units(
        (_unit("base", applicability=applicability), _unit("domain", applicability=applicability)),
        (base_mapping or _base_mapping(), domain_mapping or _domain_mapping()),
        ontology_version="waiting_periods_v2",
    )


def test_fixed_base_remains_scalar_and_legacy_product_fixed_input_is_not_emitted() -> None:
    unit = _unit("fixed")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id="fixed",
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="fixed initial wait",
                semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                semantic_value={
                    "waiting_period_type": "INITIAL",
                    "duration_value": 30,
                    "duration_unit": "DAYS",
                    "start_basis": "POLICY_INCEPTION",
                    "applies_to": ["illness treatment"],
                    "value_source": "PRODUCT_FIXED",
                },
            ),
        ),
        ontology_version="waiting_periods_v2",
    )
    value = result.semantic_facts[0].value
    assert value["duration_value"] == 30
    assert value["duration_unit"] == "DAYS"
    assert "duration_domain_reference" not in value
    assert "value_source" not in value


def test_schedule_bound_base_maps_without_scalar_or_base_value_source() -> None:
    result = _map_pair()
    base = next(fact for fact in result.semantic_facts if fact.semantic_type == "BASE_MECHANIC")
    domain = next(fact for fact in result.semantic_facts if fact.semantic_type == "DURATION_SELECTION")
    assert "duration_value" not in base.value
    assert "duration_unit" not in base.value
    assert "value_source" not in base.value
    assert base.value["duration_domain_reference"]["semantic_fact_id"] == domain.fact_id
    assert domain.value["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert tuple(item["duration_value"] for item in domain.value["duration_options"]) == (1, 2, 3)


def test_base_rejects_scalar_plus_domain_reference_as_possible_unmodeled_override() -> None:
    unit = _unit("base")
    mapping = _base_mapping()
    value = dict(mapping.semantic_value)
    value.update({"duration_value": 2, "duration_unit": "YEARS"})
    with pytest.raises(WaitingPeriodMappingError, match="future reviewed mode"):
        map_reviewed_waiting_period_units(
            (unit,),
            (
                ReviewedWaitingPeriodMapping(
                    normative_unit_id="base",
                    kind=ReviewedMappingKind.SEMANTIC_FACT,
                    reason="unsupported fixed plus schedule override",
                    semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                    semantic_value=value,
                ),
            ),
            ontology_version="waiting_periods_v2",
        )


def test_schedule_bound_base_rejects_missing_domain_fact() -> None:
    applicability = ApplicabilityKey(product_reference="product://generic")
    with pytest.raises(WaitingPeriodMappingError, match="missing semantic fact"):
        map_reviewed_waiting_period_units(
            (_unit("base", applicability=applicability),),
            (_base_mapping(),),
            ontology_version="waiting_periods_v2",
        )


def test_duration_domain_reference_rejects_waiting_period_type_mismatch() -> None:
    with pytest.raises(WaitingPeriodMappingError, match="waiting-period type mismatch"):
        _map_pair(base_mapping=_base_mapping(reference_type="PRE_EXISTING_DISEASE"))


def test_duration_domain_reference_rejects_ontology_version_mismatch() -> None:
    with pytest.raises(WaitingPeriodMappingError, match="ontology version mismatch"):
        _map_pair(base_mapping=_base_mapping(reference_ontology="waiting_periods_v1"))


def test_duration_domain_reference_rejects_scope_mismatch() -> None:
    with pytest.raises(WaitingPeriodMappingError, match="scope identity mismatch"):
        _map_pair(
            domain_mapping=_domain_mapping(
                scope_type="BENEFIT_SCOPED",
                scope_reference="investigation_cover",
            )
        )


def test_missing_policy_schedule_is_instance_bound_not_semantic_residue() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    assert resolution.status is ResolutionStatus.POLICY_SCHEDULE_BOUND


def test_duration_domain_dependency_participates_in_publication_dependency_identity() -> None:
    domain_v1 = DurationDomainDependencyBinding(
        semantic_fact_id="fact_domain_duration_selection",
        waiting_period_type="SPECIFIC_DISEASE_PROCEDURE",
        ontology_version="waiting_periods_v2",
        source_document_id="policy_wording",
        source_document_version="v1",
        source_hash_sha256="a" * 64,
    )
    domain_v2 = DurationDomainDependencyBinding(
        semantic_fact_id="fact_domain_duration_selection",
        waiting_period_type="SPECIFIC_DISEASE_PROCEDURE",
        ontology_version="waiting_periods_v2",
        source_document_id="policy_wording",
        source_document_version="v2",
        source_hash_sha256="b" * 64,
    )
    common = dict(
        ontology_version="waiting_periods_v2",
        source_document_id="base_clause",
        source_document_version="v1",
        source_hash_sha256="c" * 64,
        review_decision_version="review-v1",
    )
    published = PublicationDependencyBinding(**common, duration_domain_dependency=domain_v1)
    same = PublicationDependencyBinding(**common, duration_domain_dependency=domain_v1)
    changed = PublicationDependencyBinding(**common, duration_domain_dependency=domain_v2)
    assert dependency_binding_matches(published, same)
    assert not dependency_binding_matches(published, changed)


def test_bajaj_c6_4_adjudication_closes_true_semantic_residue_without_claiming_full_instance_resolution() -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    summary = artifact["revised_c6_summary"]
    decision = artifact["decision"]
    assert summary["atomic_unit_count"] == 30
    assert summary["accounted_unit_count"] == 30
    assert summary["true_semantic_residue_count"] == 0
    assert decision["bajaj_semantic_representation_complete"] is True
    assert decision["bajaj_all_customer_answers_resolved"] is False
    assert artifact["representability_update"]["instance_status"] == "POLICY_SCHEDULE_BOUND"
    assert artifact["dependent_relationship_update"]["resolution_class"] == "INSTANCE_BOUND"
