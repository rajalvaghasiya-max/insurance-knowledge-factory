import json
from pathlib import Path

from insurance_intelligence.generic_knowledge.waiting_period_migration import (
    migrate_waiting_period_record,
)


ACTIV_MIGRATION_PATH = Path(
    "knowledge/factory/migrations/activ_one_nxt_waiting_period_generic_migration_v1.json"
)
STAR_MIGRATION_PATH = Path(
    "knowledge/factory/migrations/star_comprehensive_waiting_period_generic_migration_v1.json"
)
REVIEW_PATH = Path(
    "docs/architecture/ACTIV_ONE_NXT_WAITING_PERIOD_REVIEW_DECISION.json"
)
SOURCE_BINDING_PATH = Path(
    "docs/architecture/ACTIV_ONE_NXT_POLICY_WORDING_SOURCE_BINDING.json"
)
MIGRATION_MODULE = Path(
    "insurance_intelligence/generic_knowledge/waiting_period_migration.py"
)


def _record():
    return json.loads(ACTIV_MIGRATION_PATH.read_text(encoding="utf-8"))


def _result():
    return migrate_waiting_period_record(_record())


def _facts_by_type():
    return {
        fact.value["waiting_period_type"]: fact
        for fact in _result().mapping.semantic_facts
    }


def test_activ_record_uses_same_generic_loader_without_product_branching():
    source = MIGRATION_MODULE.read_text(encoding="utf-8").casefold()
    assert "activ_one" not in source
    assert "aditya_birla" not in source
    assert "adihlip" not in source
    assert _record()["record_type"] == "generic_waiting_period_migration_v1"


def test_activ_source_identity_matches_certified_source_binding():
    binding = json.loads(SOURCE_BINDING_PATH.read_text(encoding="utf-8"))
    result = _result()
    assert result.source_document_id == binding["source_registration"]["document_id"]
    assert result.source_document_version == binding["certified_processed_asset"]["asset_id"]
    assert result.source_hash_sha256 == binding["source_registration"]["document_hash_sha256"]


def test_generic_migration_accounts_every_activ_unit_without_residue():
    result = _result()
    assert result.accounting.publishable
    assert result.accounting.telemetry.normative_unit_count == 3
    assert result.accounting.telemetry.accounted_unit_count == 3
    assert result.accounting.telemetry.residue_count == 0
    assert result.accounting.blockers == ()


def test_generic_migration_produces_three_activ_base_mechanics():
    facts = _facts_by_type()
    assert set(facts) == {
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "INITIAL",
    }
    assert all(fact.semantic_type == "BASE_MECHANIC" for fact in facts.values())


def test_activ_ped_preserves_schedule_delegation_and_reviewed_three_year_value():
    ped = _facts_by_type()["PRE_EXISTING_DISEASE"].value
    assert ped["duration_value"] == 3
    assert ped["duration_unit"] == "YEARS"
    assert ped["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert ped["applies_to"] == (
        "treatment of a pre-existing disease",
        "direct complications of a pre-existing disease",
    )
    assert "product benefit table" in ped["duration_evidence_note"].casefold()
    assert "policy schedule" in ped["schedule_dependency"].casefold()
    assert "portability" in ped["continuity_dependency"].casefold()
    assert "sum insured increase" in ped["sum_insured_enhancement_rule"].casefold()
    assert "declared" in ped["post_waiting_condition"].casefold()


def test_activ_specific_disease_parity_with_certified_review_decision():
    fact = _facts_by_type()["SPECIFIC_DISEASE_PROCEDURE"].value
    assert fact["duration_value"] == 24
    assert fact["duration_unit"] == "MONTHS"
    assert fact["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert fact["exceptions"] == ["claims arising due to an accident"]
    assert "longer" in fact["interaction_rule"].casefold()
    assert "contracted after" in fact["contracted_after_policy_rule"].casefold()


def test_activ_initial_waiting_period_parity_with_certified_review_decision():
    fact = _facts_by_type()["INITIAL"].value
    assert fact["duration_value"] == 30
    assert fact["duration_unit"] == "DAYS"
    assert fact["start_basis"] == "POLICY_INCEPTION"
    assert "accident" in " ".join(fact["exceptions"]).casefold()
    assert "continuous coverage" in " ".join(fact["exceptions"]).casefold()


def test_activ_generic_migration_matches_review_decision_core_mechanics():
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    facts = _facts_by_type()
    for decision in review["decisions"]:
        fact = facts[decision["waiting_period_type"]].value
        mechanics = decision["reviewed_mechanics"]
        assert fact["duration_value"] == mechanics["duration_value"]
        assert fact["duration_unit"] == mechanics["duration_unit"]
        assert fact["start_basis"] == mechanics["start_basis"]
        assert list(fact["applies_to"]) == mechanics["applies_to"]


def test_optional_waiting_period_reductions_are_not_folded_into_base_migration():
    payload = json.dumps(_record()).casefold()
    assert '"duration_value": 1' not in payload
    assert "reduction in specific disease waiting period" not in payload
    assert "c.10.1" not in payload
    assert "c.10.2" not in payload
    facts = _facts_by_type()
    assert facts["SPECIFIC_DISEASE_PROCEDURE"].value["duration_value"] == 24
    assert facts["PRE_EXISTING_DISEASE"].value["duration_value"] == 3


def test_chronic_care_waiver_is_not_silently_merged_into_base_migration():
    payload = json.dumps(_record()).casefold()
    assert "chronic care" not in payload
    assert "waives" not in payload
    facts = _facts_by_type()
    assert facts["PRE_EXISTING_DISEASE"].value["duration_value"] == 3
    assert facts["INITIAL"].value["duration_value"] == 30


def test_star_and_activ_use_same_generic_code_with_different_product_data():
    star_record = json.loads(STAR_MIGRATION_PATH.read_text(encoding="utf-8"))
    star = migrate_waiting_period_record(star_record)
    activ = _result()
    assert star.applicability.product_reference != activ.applicability.product_reference
    assert star.ontology_version == activ.ontology_version == "waiting_periods_v1"
    assert len(star.mapping.semantic_facts) == len(activ.mapping.semantic_facts) == 3
    assert star.accounting.publishable
    assert activ.accounting.publishable
    star_ped = {
        fact.value["waiting_period_type"]: fact.value
        for fact in star.mapping.semantic_facts
    }["PRE_EXISTING_DISEASE"]
    activ_ped = {
        fact.value["waiting_period_type"]: fact.value
        for fact in activ.mapping.semantic_facts
    }["PRE_EXISTING_DISEASE"]
    assert star_ped["duration_value"] == 36
    assert star_ped["duration_unit"] == "MONTHS"
    assert activ_ped["duration_value"] == 3
    assert activ_ped["duration_unit"] == "YEARS"
