from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnit,
    NormativeUnitKind,
    RelationshipType,
)
from insurance_intelligence.generic_knowledge.dependency_resolution import (
    EffectiveDependencyState,
    ResolutionOperand,
    resolve_required_inputs,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    RepresentationState,
    ResolutionInputs,
    ResolutionStatus,
    ValueSource,
    compute_resolution_status,
)
from insurance_intelligence.generic_knowledge.waiting_period_mapping import (
    ReviewedMappingKind,
    ReviewedWaitingPeriodMapping,
    WaitingPeriodSemanticType,
    map_reviewed_waiting_period_units,
)


ATOMIC_PATH = Path(
    "docs/architecture/MO_028B_G11_C6_BAJAJ_ATOMIC_WAITING_PERIOD_INVENTORY.json"
)
MAPPING_PATH = Path(
    "docs/architecture/MO_028B_G11_C6_BAJAJ_REVIEWED_WAITING_PERIOD_MAPPING.json"
)


def _atomic() -> dict:
    return json.loads(ATOMIC_PATH.read_text(encoding="utf-8"))


def _mapping() -> dict:
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def _units() -> tuple[NormativeUnit, ...]:
    record = _atomic()
    applicability = ApplicabilityKey(
        product_reference=record["product"]["entity_id"],
        policy_version=record["product"]["uin"],
    )
    units: list[NormativeUnit] = []
    for item in record["atomic_units"]:
        proposition = item["normative_proposition"]
        units.append(
            NormativeUnit(
                normative_unit_id=item["atomic_unit_id"],
                concept="waiting_periods",
                kind=NormativeUnitKind.CONDITION,
                text_sha256=hashlib.sha256(proposition.encode("utf-8")).hexdigest(),
                excerpt=item["source_support_summary"],
                applicability=applicability,
                evidence=EvidenceReference(
                    evidence_id=f'evidence_{item["atomic_unit_id"]}',
                    source_document_id=record["source"]["document_id"],
                    source_document_version="v1",
                    source_hash_sha256=record["source"]["sha256"],
                    locator=item["source_locator"],
                    authority_class=record["source"]["authority_class"],
                ),
                materially_affects=tuple(item["material_effects"]),
            )
        )
    return tuple(units)


def _reviewed_mappings() -> tuple[ReviewedWaitingPeriodMapping, ...]:
    mappings: list[ReviewedWaitingPeriodMapping] = []
    for item in _mapping()["reviewed_mappings"]:
        kind = ReviewedMappingKind[item["mapping_kind"]]
        kwargs: dict[str, object] = {
            "normative_unit_id": item["atomic_unit_id"],
            "kind": kind,
            "reason": item["reason"],
        }
        if kind is ReviewedMappingKind.SEMANTIC_FACT:
            kwargs["semantic_type"] = WaitingPeriodSemanticType[item["semantic_type"]]
            kwargs["semantic_value"] = item["semantic_value"]
        elif kind is ReviewedMappingKind.RELATIONSHIP_FACT:
            kwargs["relationship_type"] = RelationshipType[item["relationship_type"]]
            kwargs["source_concept"] = item["source_concept"]
            kwargs["target_concept"] = item["target_concept"]
            kwargs["relationship_condition"] = item["relationship_condition"]
        mappings.append(ReviewedWaitingPeriodMapping(**kwargs))
    return tuple(mappings)


def _mapped_result():
    record = _mapping()
    return map_reviewed_waiting_period_units(
        _units(), _reviewed_mappings(), ontology_version=record["ontology_version"]
    )


def test_c6_mapping_accounts_every_certified_atomic_unit_exactly_once() -> None:
    atomic_ids = {item["atomic_unit_id"] for item in _atomic()["atomic_units"]}
    mapped_ids = [item["atomic_unit_id"] for item in _mapping()["reviewed_mappings"]]
    assert len(atomic_ids) == 27
    assert len(mapped_ids) == 27
    assert len(set(mapped_ids)) == 27
    assert set(mapped_ids) == atomic_ids


def test_c6_summary_is_derived_consistent_and_preserves_true_residue() -> None:
    record = _mapping()
    counts = Counter(item["disposition"] for item in record["reviewed_mappings"])
    summary = record["mapping_summary"]
    assert summary["atomic_unit_count"] == 27
    assert summary["mapped_semantic_count"] == counts["MAPPED"] == 14
    assert summary["mapped_relationship_count"] == counts["MAPPED_AS_RELATIONSHIP"] == 11
    assert summary["true_semantic_residue_count"] == counts["NOT_YET_REPRESENTABLE"] == 2
    assert set(summary["true_semantic_residue_ids"]) == {
        "bajaj_mhc_specific_base_wait_accident_exception",
        "bajaj_mhc_investigation_initial_wait",
    }
    assert summary["product_identity_reasoning_code_added"] is False


def test_existing_g6_mapper_accepts_reviewed_bajaj_mapping_without_special_branch() -> None:
    result = _mapped_result()
    assert len(result.semantic_facts) == 14
    assert len(result.relationship_facts) == 11
    assert len(result.accounting_decisions) == 27
    states = Counter(item.accounting_state for item in result.accounting_decisions)
    assert states == {
        AccountingState.MAPPED: 14,
        AccountingState.MAPPED_AS_RELATIONSHIP: 11,
        AccountingState.NOT_YET_REPRESENTABLE: 2,
    }


def test_each_mapper_output_retains_exact_source_evidence_lineage() -> None:
    result = _mapped_result()
    semantic_by_unit = {
        decision.normative_unit_id: decision.semantic_fact_ids
        for decision in result.accounting_decisions
        if decision.accounting_state is AccountingState.MAPPED
    }
    relationship_by_unit = {
        decision.normative_unit_id: decision.relationship_fact_ids
        for decision in result.accounting_decisions
        if decision.accounting_state is AccountingState.MAPPED_AS_RELATIONSHIP
    }
    semantic_facts = {fact.fact_id: fact for fact in result.semantic_facts}
    relationship_facts = {fact.relationship_id: fact for fact in result.relationship_facts}
    for unit_id, fact_ids in semantic_by_unit.items():
        assert fact_ids
        for fact_id in fact_ids:
            assert semantic_facts[fact_id].evidence_ids == (f"evidence_{unit_id}",)
    for unit_id, relationship_ids in relationship_by_unit.items():
        assert relationship_ids
        for relationship_id in relationship_ids:
            assert relationship_facts[relationship_id].evidence_ids == (f"evidence_{unit_id}",)


def test_schedule_selected_ped_and_specific_domains_remain_instance_bound() -> None:
    result = _mapped_result()
    domains = {
        fact.value["waiting_period_type"]: fact
        for fact in result.semantic_facts
        if fact.semantic_type == "DURATION_SELECTION"
    }
    assert set(domains) == {"PRE_EXISTING_DISEASE", "SPECIFIC_DISEASE_PROCEDURE"}
    for fact in domains.values():
        assert tuple(item["duration_value"] for item in fact.value["duration_options"]) == (1, 2, 3)
        assert fact.value["value_source"] == "POLICY_SCHEDULE_SELECTED"
        assert fact.value["resolved_value_status"] == "POLICY_SCHEDULE_BOUND"


def test_maternity_and_baby_care_keep_fixed_plan1_base_plus_conditional_modifier() -> None:
    result = _mapped_result()
    base = {
        fact.value["waiting_period_type"]: fact
        for fact in result.semantic_facts
        if fact.semantic_type == "BASE_MECHANIC"
    }
    assert base["MATERNITY"].value["duration_value"] == 36
    assert base["MATERNITY"].value["duration_unit"] == "MONTHS"
    assert base["BABY_CARE"].value["duration_value"] == 36
    modifiers = [
        rel for rel in result.relationship_facts
        if rel.relationship_type is RelationshipType.MODIFIES
    ]
    assert {rel.condition["waiting_period_type"] for rel in modifiers} == {
        "MATERNITY", "BABY_CARE"
    }
    assert all(rel.condition["modifier_direction"] == "REDUCES" for rel in modifiers)
    assert all(rel.condition["instance_condition_required"] is True for rel in modifiers)


def test_specific_longer_of_relationship_is_accounted_but_operand_block_can_propagate() -> None:
    result = _mapped_result()
    relationship = next(
        rel for rel in result.relationship_facts
        if rel.condition.get("operator") == "LONGER_OF"
    )
    assert relationship.relationship_type is RelationshipType.DERIVES_FROM

    applicability = _units()[0].applicability
    resolved = compute_resolution_status(ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED))
    blocked = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.PRODUCT_RESOLVED,
            representation_state=RepresentationState.NOT_YET_REPRESENTABLE,
        )
    )
    effective = resolve_required_inputs(
        (
            ResolutionOperand("ped", resolved, applicability, resolution_cell_identity=("wp", "base")),
            ResolutionOperand("specific", blocked, applicability, resolution_cell_identity=("wp", "base")),
        )
    )
    assert effective.effective_state is EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    assert effective.dependency_resolution is not None
    assert effective.dependency_resolution.status is ResolutionStatus.OPERAND_REPRESENTATIONALLY_BLOCKED


def test_c6_report_does_not_flatten_instance_governance_or_residue_states() -> None:
    report = {item["atomic_unit_id"]: item for item in _mapping()["representability_report"]}
    assert report["bajaj_mhc_ped_duration_selection_domain"] == {
        "atomic_unit_id": "bajaj_mhc_ped_duration_selection_domain",
        "resolution_class": "INSTANCE_BOUND",
        "answer_shape": "UNQUANTIFIED",
    }
    migration = report["bajaj_mhc_migration_continuity_general"]
    assert migration["resolution_class"] == "GOVERNANCE_BLOCKED"
    assert migration["answer_shape"] == "UNQUANTIFIED"
    assert migration["regulatory_effect_class"] == "BENEFIT_ESTABLISHING"
    assert report["bajaj_mhc_specific_base_wait_accident_exception"]["resolution_class"] == "TRUE_SEMANTIC_RESIDUE"
    assert report["bajaj_mhc_specific_longer_of_ped_relationship"]["resolution_class"] == "DEPENDENCY_BLOCKED"


def test_benefit_scope_cataract_and_daycare_stay_relationships_not_scalar_facts() -> None:
    result = _mapped_result()
    targets = {rel.target_concept: rel for rel in result.relationship_facts}
    investigation = targets["doctor_prescribed_lab_and_radiology_cover"]
    assert investigation.relationship_type in {RelationshipType.DEPENDS_ON, RelationshipType.APPLIES_WHEN}
    assert targets["cataract_payment"].condition["cost_sharing_semantics"] == "SEPARATE"
    assert targets["day_care_procedures"].relationship_type is RelationshipType.DEPENDS_ON


def test_c6_mapping_does_not_claim_bajaj_publication_ready() -> None:
    decision = _mapping()["review_decision"]
    assert decision["all_atomic_units_accounted"] is True
    assert decision["bajaj_publication_ready"] is False
    assert "two" in decision["reason"].casefold()


def test_generic_reasoning_modules_still_contain_no_bajaj_product_branch() -> None:
    paths = (
        Path("insurance_intelligence/generic_knowledge/waiting_period_mapping.py"),
        Path("insurance_intelligence/generic_knowledge/resolution_status.py"),
        Path("insurance_intelligence/generic_knowledge/dependency_resolution.py"),
        Path("insurance_intelligence/generic_knowledge/waiting_period_resolution_cell.py"),
        Path("insurance_intelligence/generic_knowledge/waiting_period_schedule_resolution.py"),
        Path("insurance_intelligence/generic_knowledge/governance_integration.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8").casefold() for path in paths)
    for forbidden in (
        "bajaj_allianz",
        "my_health_care",
        "bajh lip",
        "if insurer",
        "if product ==",
    ):
        assert forbidden not in source
