from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnit,
    NormativeUnitKind,
)
from insurance_intelligence.generic_knowledge.waiting_period_mapping import (
    ReviewedMappingKind,
    ReviewedWaitingPeriodMapping,
    WaitingPeriodMappingError,
    WaitingPeriodSemanticType,
    map_reviewed_waiting_period_units,
)


ATOMIC_V1 = Path(
    "docs/architecture/MO_028B_G11_C6_BAJAJ_ATOMIC_WAITING_PERIOD_INVENTORY.json"
)
MAPPING_V1 = Path(
    "docs/architecture/MO_028B_G11_C6_BAJAJ_REVIEWED_WAITING_PERIOD_MAPPING.json"
)
RESEGMENTATION = Path(
    "docs/architecture/MO_028B_G11_C6_3_BAJAJ_PROVENANCE_RESEGMENTATION.json"
)
REVISED_MAPPING = Path(
    "docs/architecture/MO_028B_G11_C6_3_BAJAJ_REVISED_MAPPING_ADJUDICATION.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _replacement_units() -> list[dict]:
    units: list[dict] = []
    for replacement in _load(RESEGMENTATION)["replacements"]:
        units.extend(replacement["replacement_units"])
    return units


def _virtual_revised_ids() -> set[str]:
    base = {item["atomic_unit_id"] for item in _load(ATOMIC_V1)["atomic_units"]}
    removed = {
        replacement["replaces_atomic_unit_id"]
        for replacement in _load(RESEGMENTATION)["replacements"]
    }
    added = {item["atomic_unit_id"] for item in _replacement_units()}
    return (base - removed) | added


def _unit(item: dict) -> NormativeUnit:
    record = _load(ATOMIC_V1)
    proposition = item["normative_proposition"]
    return NormativeUnit(
        normative_unit_id=item["atomic_unit_id"],
        concept="waiting_periods",
        kind=NormativeUnitKind.CONDITION,
        text_sha256=hashlib.sha256(proposition.encode("utf-8")).hexdigest(),
        excerpt=item["source_support_summary"],
        applicability=ApplicabilityKey(
            product_reference=record["product"]["entity_id"],
            policy_version=record["product"]["uin"],
        ),
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


def _reviewed(item: dict) -> ReviewedWaitingPeriodMapping:
    kind = ReviewedMappingKind[item["mapping_kind"]]
    kwargs: dict[str, object] = {
        "normative_unit_id": item["atomic_unit_id"],
        "kind": kind,
        "reason": item["reason"],
    }
    if kind is ReviewedMappingKind.SEMANTIC_FACT:
        kwargs["semantic_type"] = WaitingPeriodSemanticType[item["semantic_type"]]
        kwargs["semantic_value"] = item["semantic_value"]
    return ReviewedWaitingPeriodMapping(**kwargs)


def test_c6_3_provenance_rule_replaces_only_the_two_composite_units() -> None:
    record = _load(RESEGMENTATION)
    assert record["decision_rule"]["name"] == "PROVENANCE_SEPARABILITY"
    assert {
        item["replaces_atomic_unit_id"] for item in record["replacements"]
    } == {
        "bajaj_mhc_specific_base_wait_accident_exception",
        "bajaj_mhc_investigation_initial_wait",
    }
    assert len(_replacement_units()) == 5


def test_revised_virtual_inventory_has_thirty_unique_source_supported_units() -> None:
    revised_ids = _virtual_revised_ids()
    assert len(revised_ids) == 30
    assert "bajaj_mhc_specific_base_wait_accident_exception" not in revised_ids
    assert "bajaj_mhc_investigation_initial_wait" not in revised_ids
    assert {
        "bajaj_mhc_specific_base_wait_schedule_bound",
        "bajaj_mhc_specific_accident_exception",
        "bajaj_mhc_specific_schedule_dependency",
        "bajaj_mhc_investigation_initial_30_day_wait",
        "bajaj_mhc_investigation_initial_wait_renewal_cessation",
    } <= revised_ids
    assert all(
        item["source_sufficiency_review"] == "CONFIRMED"
        for item in _replacement_units()
    )


def test_resegmentation_preserves_clause_group_lineage_and_no_mixed_accounting() -> None:
    record = _load(RESEGMENTATION)
    assert {item["parent_clause_group_id"] for item in record["replacements"]} == {
        "cg_specific",
        "cg_investigation_initial",
    }
    summary = record["revised_inventory_summary"]
    assert summary["original_clause_group_count"] == 13
    assert summary["revised_atomic_unit_count"] == 30
    assert summary["source_sufficiency_confirmed_count"] == 30
    assert summary["mixed_accounting_allowed"] is False


def test_revised_mapping_summary_reduces_true_residue_from_two_to_one() -> None:
    old = _load(MAPPING_V1)["mapping_summary"]
    revised = _load(REVISED_MAPPING)["revised_mapping_summary"]
    assert old["true_semantic_residue_count"] == 2
    assert revised == {
        "atomic_unit_count": 30,
        "mapped_semantic_count": 18,
        "mapped_relationship_count": 11,
        "true_semantic_residue_count": 1,
        "true_semantic_residue_ids": [
            "bajaj_mhc_specific_base_wait_schedule_bound"
        ],
        "product_identity_reasoning_code_added": False,
        "mixed_accounting_added": False,
        "new_generic_semantic_contract_added": False,
    }


def test_four_new_source_separable_propositions_map_with_existing_g6_contract() -> None:
    units_by_id = {item["atomic_unit_id"]: item for item in _replacement_units()}
    mapping_record = _load(REVISED_MAPPING)
    mapped_items = [
        item
        for item in mapping_record["replacement_dispositions"]
        if item["mapping_kind"] == "SEMANTIC_FACT"
    ]
    units = tuple(_unit(units_by_id[item["atomic_unit_id"]]) for item in mapped_items)
    mappings = tuple(_reviewed(item) for item in mapped_items)
    result = map_reviewed_waiting_period_units(
        units, mappings, ontology_version="waiting_periods_v2"
    )
    assert len(result.semantic_facts) == 4
    assert len(result.relationship_facts) == 0
    assert Counter(fact.semantic_type for fact in result.semantic_facts) == {
        "EXCEPTION": 1,
        "SCHEDULE_DEPENDENCY": 1,
        "BASE_MECHANIC": 1,
        "RENEWAL_EFFECT": 1,
    }


def test_investigation_wait_and_renewal_cessation_keep_distinct_evidence_lineage() -> None:
    units = {item["atomic_unit_id"]: item for item in _replacement_units()}
    first_year = units["bajaj_mhc_investigation_initial_30_day_wait"]
    renewal = units["bajaj_mhc_investigation_initial_wait_renewal_cessation"]
    assert first_year["source_line_range"] != renewal["source_line_range"]
    assert "30-day" in first_year["normative_proposition"]
    assert "renewal" in renewal["normative_proposition"].lower()


def test_specific_accident_and_schedule_dependency_keep_distinct_evidence_lineage() -> None:
    units = {item["atomic_unit_id"]: item for item in _replacement_units()}
    accident = units["bajaj_mhc_specific_accident_exception"]
    schedule = units["bajaj_mhc_specific_schedule_dependency"]
    assert accident["source_line_range"] != schedule["source_line_range"]
    assert accident["material_effects"] == ["EXCEPTION", "APPLICABILITY"]
    assert schedule["material_effects"] == ["SCHEDULE_DEPENDENCY", "APPLICABILITY"]


def test_pre_c6_4_schedule_bound_base_shape_is_rejected_not_artifact_bookkeeping() -> None:
    units = {item["atomic_unit_id"]: item for item in _replacement_units()}
    base_unit = _unit(units["bajaj_mhc_specific_base_wait_schedule_bound"])
    # C6.3 only needs to prove that its pre-C6.4 mapping shape was genuinely
    # unrepresentable. C6.4 intentionally changed which invariant rejects that
    # legacy shape, so this historical certification must not pin one error string.
    with pytest.raises(WaitingPeriodMappingError):
        map_reviewed_waiting_period_units(
            (base_unit,),
            (
                ReviewedWaitingPeriodMapping(
                    normative_unit_id=base_unit.normative_unit_id,
                    kind=ReviewedMappingKind.SEMANTIC_FACT,
                    reason="prove pre-C6.4 BASE_MECHANIC limitation",
                    semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                    semantic_value={
                        "waiting_period_type": "SPECIFIC_DISEASE_PROCEDURE",
                        "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
                        "applies_to": ["specified diseases and procedures"],
                        "scope_type": "POLICY_WIDE",
                        "value_source": "POLICY_SCHEDULE_SELECTED",
                    },
                ),
            ),
            ontology_version="waiting_periods_v2",
        )


def test_remaining_residue_is_accounted_fail_closed_without_new_contract() -> None:
    units_by_id = {item["atomic_unit_id"]: item for item in _replacement_units()}
    residue_item = next(
        item
        for item in _load(REVISED_MAPPING)["replacement_dispositions"]
        if item["mapping_kind"] == "NOT_YET_REPRESENTABLE"
    )
    unit = _unit(units_by_id[residue_item["atomic_unit_id"]])
    result = map_reviewed_waiting_period_units(
        (unit,), (_reviewed(residue_item),), ontology_version="waiting_periods_v2"
    )
    assert len(result.semantic_facts) == 0
    assert len(result.relationship_facts) == 0
    assert result.accounting_decisions[0].accounting_state.value == "NOT_YET_REPRESENTABLE"


def test_c6_3_does_not_introduce_option_b_option_c_or_mixed_accounting() -> None:
    adjudication = _load(RESEGMENTATION)["adjudication"]
    assert adjudication["new_base_mechanic_qualifier_fields_required"] is False
    assert adjudication["multi_output_mapping_required"] is False
    assert adjudication["generic_proposition_wrapper_required"] is False
    decision = _load(REVISED_MAPPING)["decision"]
    assert decision["remaining_residue_count"] == 1
    assert decision["bajaj_publication_ready"] is False
