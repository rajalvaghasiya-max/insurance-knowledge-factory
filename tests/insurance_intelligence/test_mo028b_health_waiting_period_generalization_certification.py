from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.generic_knowledge.waiting_period_migration import (
    migrate_waiting_period_record,
)


CERT = Path(
    "docs/architecture/MO_028B_HEALTH_WAITING_PERIOD_GENERALIZATION_CERTIFICATION.json"
)
STAR = Path(
    "knowledge/factory/migrations/star_comprehensive_waiting_period_generic_migration_v1.json"
)
ACTIV = Path(
    "knowledge/factory/migrations/activ_one_nxt_waiting_period_generic_migration_v1.json"
)
ACTIV_REVIEW = Path(
    "docs/architecture/ACTIV_ONE_NXT_WAITING_PERIOD_REVIEW_DECISION.json"
)
BAJAJ_CLOSURE = Path(
    "docs/architecture/MO_028B_G11_BAJAJ_ADVERSARIAL_CLOSURE_CERTIFICATION.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _facts_by_type(result) -> dict[str, dict]:
    return {
        fact.value["waiting_period_type"]: dict(fact.value)
        for fact in result.mapping.semantic_facts
        if "waiting_period_type" in fact.value
    }


def test_mo028b_certification_names_three_distinct_pressure_roles() -> None:
    record = _load(CERT)
    roles = {item["role"] for item in record["pressure_products"]}
    assert roles == {
        "LEGACY_BACKWARD_COMPATIBILITY",
        "GOVERNED_PUBLICATION_BOUNDARY",
        "ADVERSARIAL_GENERALIZATION",
    }
    assert {item["product"] for item in record["pressure_products"]} == {
        "Star Comprehensive",
        "Activ One NXT",
        "My Health Care Plan",
    }


def test_star_recertifies_under_v2_without_semantic_drift_or_residue() -> None:
    record = _load(STAR)
    v1 = migrate_waiting_period_record(record)
    v2 = migrate_waiting_period_record(record, ontology_version_override="waiting_periods_v2")
    assert v1.accounting.publishable is True
    assert v2.accounting.publishable is True
    assert v2.accounting.telemetry.residue_count == 0
    assert _facts_by_type(v1) == _facts_by_type(v2)
    assert all(fact.ontology_version == "waiting_periods_v2" for fact in v2.mapping.semantic_facts)


def test_activ_recertifies_under_v2_and_keeps_governed_publication_boundary() -> None:
    record = _load(ACTIV)
    v1 = migrate_waiting_period_record(record)
    v2 = migrate_waiting_period_record(record, ontology_version_override="waiting_periods_v2")
    assert v1.accounting.publishable is True
    assert v2.accounting.publishable is True
    assert v2.accounting.telemetry.residue_count == 0
    assert _facts_by_type(v1) == _facts_by_type(v2)

    review = _load(ACTIV_REVIEW)
    boundary = review["publication_boundary"]
    assert review["reviewed_by_human"] is True
    assert review["review_status"] == "APPROVED_FOR_GOVERNED_PROJECTION"
    assert boundary["human_base_clause_review_approved"] is True
    assert boundary["runtime_publication_created"] is True
    assert boundary["authoritative_publication_created"] is True
    assert boundary["coverage_registry_promoted"] is True


def test_bajaj_closure_proves_zero_residue_without_collapsing_unresolved_states() -> None:
    closure = _load(BAJAJ_CLOSURE)
    representation = closure["semantic_representability"]
    safety = closure["resolution_safety"]
    publication = closure["publication_safety"]
    decision = closure["decision"]

    assert representation["atomic_unit_count"] == 30
    assert representation["accounted_unit_count"] == 30
    assert representation["true_semantic_residue_count"] == 0
    assert safety["policy_schedule_selected_waits"]["status_without_instance_schedule"] == "POLICY_SCHEDULE_BOUND"
    assert safety["longer_of_dependency"]["status_before_required_schedule_operands_resolve"] == "OPERAND_INSTANCE_BOUND"
    assert safety["conditional_modifiers"]["state_without_instance_condition"] == "CONDITIONAL_RANGE"
    assert safety["migration"]["effective_credit_status"] == "REGULATORY_VERIFICATION_REQUIRED"
    assert safety["migration"]["answer_shape"] == "UNQUANTIFIED"
    assert safety["migration"]["affirmative_effective_benefit_publishable"] is False
    assert safety["all_customer_answers_resolved"] is False
    assert publication["zero_residue_implies_publication_ready"] is False
    assert publication["publication_requires_existing_g7_c5_governance_gates"] is True
    assert decision["g11_closed"] is True
    assert decision["g11_certified"] is True


def test_final_certification_preserves_scope_limits_and_does_not_overclaim() -> None:
    record = _load(CERT)
    limits = record["scope_limits"]
    not_certified = set(limits["not_certified_by_this_milestone"])
    assert "all Health benefit families" in not_certified
    assert "claims adjudication" in not_certified
    assert "Life or Motor insurance semantics" in not_certified
    assert "exact current migration credit without regulatory verification" in not_certified
    assert record["decision"]["mo028b_health_waiting_period_generalization_complete"] is True
    assert record["decision"]["mo028b_ready_for_final_certification_tests"] is True
    assert record["decision"]["mo028b_closed"] is False


def test_final_certification_keeps_core_safety_invariants_explicit() -> None:
    invariants = set(_load(CERT)["safety_invariants"])
    expected = {
        "INSTANCE_BOUND_IS_NOT_RESIDUE",
        "ZERO_RESIDUE_DOES_NOT_MEAN_FULL_INSTANCE_RESOLUTION",
        "ZERO_RESIDUE_DOES_NOT_MEAN_AUTOMATIC_PUBLICATION",
        "CONDITIONAL_IS_NOT_SCALAR",
        "REGULATORY_VERIFICATION_REQUIRED_IS_NOT_AFFIRMATIVE_EFFECTIVE_BENEFIT",
        "MACHINE_REVIEW_REQUEST_IS_NOT_HUMAN_APPROVAL",
        "PRODUCT_IDENTITY_IS_DATA_NOT_REASONING",
        "FINEST_PUBLISHABLE_UNIT_GATING",
    }
    assert expected <= invariants


def test_generic_waiting_period_reasoning_contains_no_pressure_product_branches() -> None:
    paths = (
        Path("insurance_intelligence/generic_knowledge/waiting_period_mapping.py"),
        Path("insurance_intelligence/generic_knowledge/waiting_period_migration.py"),
        Path("insurance_intelligence/generic_knowledge/resolution_status.py"),
        Path("insurance_intelligence/generic_knowledge/dependency_resolution.py"),
        Path("insurance_intelligence/generic_knowledge/waiting_period_resolution_cell.py"),
        Path("insurance_intelligence/generic_knowledge/waiting_period_schedule_resolution.py"),
        Path("insurance_intelligence/generic_knowledge/waiting_period_duration_domain.py"),
        Path("insurance_intelligence/generic_knowledge/governance_integration.py"),
        Path("insurance_intelligence/generic_knowledge/publication_eligibility.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8").casefold() for path in paths)
    for forbidden in (
        "star_health",
        "star_comprehensive",
        "aditya_birla",
        "activ_one",
        "bajaj_allianz",
        "my_health_care",
        "if insurer",
        "if product ==",
    ):
        assert forbidden not in source
