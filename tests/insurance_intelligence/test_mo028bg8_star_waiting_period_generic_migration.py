import json
from pathlib import Path

from insurance_intelligence.benefits.star_comprehensive_waiting_periods import (
    STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION,
)
from insurance_intelligence.generic_knowledge.waiting_period_migration import (
    migrate_waiting_period_record,
)


MIGRATION_PATH = Path(
    "knowledge/factory/migrations/star_comprehensive_waiting_period_generic_migration_v1.json"
)
REVIEW_PATH = Path(
    "docs/architecture/STAR_COMPREHENSIVE_WAITING_PERIOD_REVIEW_DECISION.json"
)
MIGRATION_MODULE = Path(
    "insurance_intelligence/generic_knowledge/waiting_period_migration.py"
)


def _record():
    return json.loads(MIGRATION_PATH.read_text(encoding="utf-8"))


def _result():
    return migrate_waiting_period_record(_record())


def _facts_by_type():
    return {
        fact.value["waiting_period_type"]: fact
        for fact in _result().mapping.semantic_facts
    }


def test_generic_migration_record_is_data_not_product_reasoning_code():
    record = _record()
    assert record["record_type"] == "generic_waiting_period_migration_v1"
    assert record["product_reference"] == STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION.product_variant_id
    source = MIGRATION_MODULE.read_text(encoding="utf-8").casefold()
    assert "star_health" not in source
    assert "star_comprehensive" not in source
    assert "shahlip" not in source


def test_star_source_identity_matches_certified_publication():
    result = _result()
    legacy = STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION
    assert result.source_document_id == legacy.source_document_id
    assert result.source_document_version == legacy.source_document_version_id
    assert result.source_hash_sha256 == legacy.source_document_sha256


def test_generic_migration_accounts_every_star_unit_without_residue():
    result = _result()
    assert result.accounting.publishable
    assert result.accounting.telemetry.normative_unit_count == 3
    assert result.accounting.telemetry.accounted_unit_count == 3
    assert result.accounting.telemetry.residue_count == 0
    assert result.accounting.blockers == ()


def test_generic_migration_produces_three_base_mechanics():
    facts = _facts_by_type()
    assert set(facts) == {
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "INITIAL",
    }
    assert all(fact.semantic_type == "BASE_MECHANIC" for fact in facts.values())


def test_ped_parity_with_certified_review_decision():
    ped = _facts_by_type()["PRE_EXISTING_DISEASE"].value
    assert ped["duration_value"] == 36
    assert ped["duration_unit"] == "MONTHS"
    assert ped["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert ped["applies_to"] == (
        "treatment of a pre-existing disease",
        "direct complications of a pre-existing disease",
    )
    assert "portability" in ped["continuity_dependency"].casefold()
    assert "sum insured increase" in ped["sum_insured_enhancement_rule"].casefold()
    assert "declared" in ped["post_waiting_condition"].casefold()


def test_specific_disease_parity_with_certified_review_decision():
    fact = _facts_by_type()["SPECIFIC_DISEASE_PROCEDURE"].value
    assert fact["duration_value"] == 24
    assert fact["duration_unit"] == "MONTHS"
    assert fact["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert fact["exceptions"] == ["claims arising due to an accident"]
    assert "longer" in fact["interaction_rule"].casefold()
    assert "contracted after" in fact["contracted_after_policy_rule"].casefold()


def test_initial_waiting_period_parity_with_certified_review_decision():
    fact = _facts_by_type()["INITIAL"].value
    assert fact["duration_value"] == 30
    assert fact["duration_unit"] == "DAYS"
    assert fact["start_basis"] == "POLICY_INCEPTION"
    assert "accident" in " ".join(fact["exceptions"]).casefold()
    assert "continuous coverage" in " ".join(fact["exceptions"]).casefold()


def test_generic_migration_matches_review_decision_core_mechanics():
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    facts = _facts_by_type()
    for decision in review["decisions"]:
        fact = facts[decision["waiting_period_type"]].value
        mechanics = decision["reviewed_mechanics"]
        assert fact["duration_value"] == mechanics["duration_value"]
        assert fact["duration_unit"] == mechanics["duration_unit"]
        assert fact["start_basis"] == mechanics["start_basis"]
        assert list(fact["applies_to"]) == mechanics["applies_to"]


def test_optional_buy_back_is_not_folded_into_base_migration():
    payload = json.dumps(_record()).casefold()
    assert '"duration_value": 12' not in payload
    assert "optional cover buy back" not in payload
    facts = _facts_by_type()
    assert facts["PRE_EXISTING_DISEASE"].value["duration_value"] == 36


def test_generic_facts_preserve_star_product_as_applicability_data_only():
    result = _result()
    assert result.applicability.product_reference == (
        "pv_star_health_star_comprehensive_shahlip26044v092526"
    )
    for fact in result.mapping.semantic_facts:
        assert fact.applicability == result.applicability
        assert fact.ontology_version == "waiting_periods_v1"
        assert fact.evidence_ids
