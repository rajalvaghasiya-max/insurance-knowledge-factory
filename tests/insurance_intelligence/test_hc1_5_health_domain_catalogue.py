from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.contracts.health_domain_registry import (
    ClaimAspect,
    DomainKnowledgeMaturity,
    DomainKnowledgeRecord,
    KnowledgePlane,
    domain_knowledge_can_answer,
)


CATALOGUE_PATH = Path(
    "knowledge/health/domain_catalogue/health_domain_vocabulary_catalogue_v1.json"
)


def _catalogue() -> dict:
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def test_catalogue_is_open_world_and_does_not_publish_completion_metrics() -> None:
    catalogue = _catalogue()
    invariants = catalogue["invariants"]

    assert catalogue["catalogue_status"] == "OPEN_WORLD_SEED"
    assert invariants["unknown_variant_space_open"] is True
    assert invariants["known_gap_set_claimed_exhaustive"] is False
    assert invariants["completion_percentage_authorized"] is False
    assert invariants["domain_knowledge_may_answer_instance_specific_query"] is False
    assert invariants["typed_product_semantics_may_be_authored_without_evidence_pressure"] is False
    assert "completion_percentage" not in set(_walk_keys(catalogue))
    assert domain_knowledge_can_answer(instance_context_in_scope=True) is False


def test_all_mature_catalogue_entries_instantiate_frozen_domain_knowledge_contract() -> None:
    catalogue = _catalogue()
    concepts = catalogue["concepts"]

    assert len(concepts) >= 20
    assert len({item["concept_id"] for item in concepts}) == len(concepts)
    assert len({item["canonical_label"] for item in concepts}) == len(concepts)

    for item in concepts:
        maturity = DomainKnowledgeMaturity(item["domain_knowledge_maturity"])
        record = DomainKnowledgeRecord(
            concept_id=item["concept_id"],
            maturity=maturity,
            authoritative_definition_refs=tuple(item["authoritative_definition_refs"]),
            boundary_notes=tuple(item["boundary_notes"]),
            unknown_variant_space_open=True,
        )
        assert record.unknown_variant_space_open is True
        assert item["definition_summary"].strip()
        assert item["important_questions"]
        assert all(question.strip().endswith("?") for question in item["important_questions"])


def test_claim_aspects_use_contextual_plane_assignment_without_global_concept_plane() -> None:
    catalogue = _catalogue()
    multi_plane_concepts = set()

    for item in catalogue["concepts"]:
        planes = set()
        for raw in item["claim_aspects"]:
            aspect = ClaimAspect(
                aspect_id=raw["aspect_id"],
                concept_id=item["concept_id"],
                plane=KnowledgePlane(raw["plane"]),
                claim_type=raw["claim_type"],
                authority_context=raw["authority_context"],
            )
            assert aspect.concept_id == item["concept_id"]
            planes.add(aspect.plane)
        assert planes
        if len(planes) > 1:
            multi_plane_concepts.add(item["concept_id"])

    assert "health:waiting_period" in multi_plane_concepts
    assert "health:pre_existing_disease" in multi_plane_concepts
    assert "health:copayment" in multi_plane_concepts
    assert "health:portability" in multi_plane_concepts


def test_current_regulatory_facts_are_effective_context_not_timeless_product_values() -> None:
    catalogue = _catalogue()
    for item in catalogue["concepts"]:
        for fact in item.get("current_regulatory_facts", []):
            assert fact["as_of_date"] == catalogue["as_of_date"]
            assert fact["authority_ref"].startswith("irdai_health_dept_faq_2024_framework#")
            assert "product_id" not in fact
            assert "insurer_id" not in fact

    waiting = next(item for item in catalogue["concepts"] if item["concept_id"] == "health:waiting_period")
    assert waiting["current_regulatory_facts"][0]["value"] == 36
    assert waiting["current_regulatory_facts"][0]["unit"] == "MONTHS"

    moratorium = next(item for item in catalogue["concepts"] if item["concept_id"] == "health:moratorium_period")
    assert moratorium["current_regulatory_facts"][0]["value"] == 60
    assert moratorium["current_regulatory_facts"][0]["unit"] == "CONTINUOUS_MONTHS"


def test_catalogue_preserves_critical_concept_boundaries() -> None:
    catalogue = _catalogue()
    by_id = {item["concept_id"]: item for item in catalogue["concepts"]}

    waiting = " ".join(by_id["health:waiting_period"]["boundary_notes"]).lower()
    assert "regulatory maximum" in waiting
    assert "personal underwriting-specific" in waiting

    ped = " ".join(by_id["health:pre_existing_disease"]["boundary_notes"]).lower()
    assert "regulatory ped definition" in ped
    assert "product's ped waiting-period implementation" in ped

    copay = " ".join(by_id["health:copayment"]["boundary_notes"]).lower()
    assert "distinct from a deductible" in copay
    assert "customer-selected" in copay

    cashless = " ".join(by_id["health:cashless_facility"]["boundary_notes"]).lower()
    assert "not a guarantee" in cashless
    assert "claimsoperational" not in cashless  # plane is structural, not prose authority laundering

    migration = by_id["health:migration"]["definition_summary"].lower()
    portability = by_id["health:portability"]["definition_summary"].lower()
    assert "same insurer" in migration
    assert "another insurer" in portability

    moratorium = " ".join(by_id["health:moratorium_period"]["boundary_notes"]).lower()
    assert "not a waiting period" in moratorium
    assert "fraud" in moratorium

    tpa = " ".join(by_id["health:third_party_administrator"]["boundary_notes"]).lower()
    assert "not the insurer" in tpa


def test_copayment_dk3_reuses_governed_meaning_asset_but_keeps_instance_guard() -> None:
    catalogue = _catalogue()
    copay = next(item for item in catalogue["concepts"] if item["concept_id"] == "health:copayment")
    source = catalogue["authoritative_sources"]["policyscna_copay_governed_meaning_asset_v1"]

    assert copay["domain_knowledge_maturity"] == "DK3_EXPLANATION_READY"
    assert "policyscna_copay_governed_meaning_asset_v1" in copay["authoritative_definition_refs"]
    assert Path(source["path"]).is_file()
    assert "customer" in source["use_boundary"].lower()
    assert domain_knowledge_can_answer(instance_context_in_scope=True) is False


def test_observed_pending_vocabulary_is_backlog_not_false_maturity() -> None:
    catalogue = _catalogue()
    mature_ids = {item["concept_id"].split(":", 1)[1] for item in catalogue["concepts"]}
    pending = catalogue["observed_terms_pending_authoritative_definition_or_boundary_review"]

    assert len(pending) >= 15
    assert len(pending) == len(set(pending))
    assert not (mature_ids & set(pending))
    assert "room_rent_limit" in pending
    assert "network_hospital" in pending
    assert "restoration_of_sum_insured" in pending
    assert "personal_waiting_period" in pending


def test_catalogue_does_not_embed_product_semantic_or_customer_decision_records() -> None:
    catalogue = _catalogue()
    keys = set(_walk_keys(catalogue))

    forbidden = {
        "product_semantic_maturity",
        "blocking_state",
        "customer_answer",
        "recommendation",
        "claim_payment_decision",
        "selected_copayment_percentage",
        "customer_specific_waiting_period_duration"
    }
    assert not (keys & forbidden)


def test_authoritative_source_registry_is_regulator_anchored_and_currentness_dated() -> None:
    catalogue = _catalogue()
    sources = catalogue["authoritative_sources"]
    faq = sources["irdai_health_dept_faq_2024_framework"]
    circular = sources["irdai_master_circular_health_2024_listing"]

    assert faq["publisher"] == "Insurance Regulatory and Development Authority of India"
    assert faq["url"] == "https://irdai.gov.in/health-dept"
    assert faq["currentness_checked_on"] == "2026-08-24"
    assert "Insurance Products" in faq["framework_note"]

    assert circular["reference_number"] == "IRDAI/HLT/CIR/PRO/84/5/2024"
    assert circular["date"] == "2024-05-29"
    assert circular["status_observed"] == "Non-Archived"
    assert circular["currentness_checked_on"] == "2026-08-24"
