import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOSURE_PATH = ROOT / "docs/architecture/insurance_intelligence/P2_7_FINAL_CERTIFICATION_CLOSURE.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_final_closure_is_versioned_and_passed() -> None:
    closure = _load(CLOSURE_PATH)

    assert closure["schema_version"] == "1.0"
    assert closure["record_id"] == "p2-7-final-certification-closure"
    assert closure["unit_id"] == "P2.7"
    assert closure["decision"] == "PASS"
    assert closure["generic_capability_decision"] == "PASS"
    assert closure["star_pilot_decision"] == "PASS"


def test_all_prerequisite_units_are_present_and_passed() -> None:
    closure = _load(CLOSURE_PATH)
    prerequisites = {item["unit_id"]: item for item in closure["prerequisite_units"]}

    assert set(prerequisites) == {"P2.1", "P2.2", "P2.3", "P2.4", "P2.5", "P2.6"}
    assert all(item["decision"] == "PASS" for item in prerequisites.values())

    for item in prerequisites.values():
        assert item["capability"]
        assert item["evidence"]
        for relative_path in item["evidence"]:
            assert (ROOT / relative_path).is_file(), relative_path


def test_star_certified_scope_covers_three_topics_and_rule_families() -> None:
    closure = _load(CLOSURE_PATH)
    scope = closure["certified_scope"]

    assert scope["domain"] == "health"
    assert scope["insurer_id"] == "star_health"
    assert scope["product_id"] == "star_comprehensive"
    assert set(scope["certified_topics"]) == {
        "conditional_copayment",
        "room_rent",
        "bariatric_surgery",
    }
    assert set(scope["certified_rule_families"]) == {
        "conditional_obligation",
        "coverage_limit",
        "eligibility_condition",
    }


def test_p2_5_and_p2_6_machine_readable_decisions_are_passed() -> None:
    p2_5 = _load(
        ROOT / "docs/architecture/insurance_intelligence/P2_5_ADVERSARIAL_EVALUATION_CLOSURE.json"
    )
    p2_6 = _load(ROOT / "docs/architecture/insurance_intelligence/P2_6_BYPASS_INVENTORY.json")

    assert p2_5["decision"] == "PASS"
    assert p2_5["scope"]["generic_capability"] == "PASS"
    assert p2_5["scope"]["star_pilot_proof"] == "PASS"

    assert p2_6["generic_capability_decision"] == "PASS"
    assert p2_6["star_pilot_decision"] == "PASS"
    assert p2_6["inventory_summary"]["active_ungoverned_paths"] == 0
    assert p2_6["star_reachability_proof"]["legacy_runtime_imports_found"] == 0
    assert p2_6["star_reachability_proof"]["legacy_static_artifact_reads_found"] == 0


def test_final_controls_remain_fail_closed_at_scope_boundary() -> None:
    controls = _load(CLOSURE_PATH)["final_controls"]

    assert controls["topic_completeness_enforced"] is True
    assert controls["multiple_rule_families_certified"] is True
    assert controls["publication_decision_proven"] is True
    assert controls["authoritative_publication_proven"] is True
    assert controls["adversarial_evaluation_passed"] is True
    assert controls["active_ungoverned_recommendation_paths"] == 0
    assert controls["legacy_paths_certified_pilot_reachable"] == 0

    assert controls["claim_payment_guarantee_certified"] is False
    assert controls["product_recommendation_certified"] is False
    assert controls["individualized_suitability_certified"] is False


def test_closure_preserves_explicit_limitations_and_full_suite_requirement() -> None:
    closure = _load(CLOSURE_PATH)
    limitations = " ".join(closure["limitations"]).lower()

    assert "star comprehensive pilot only" in limitations
    assert "does not certify product comparison" in limitations
    assert "does not guarantee claim" in limitations
    assert "new governed review" in limitations

    validation = closure["validation_evidence"]
    assert validation["p2_6_post_merge_full_repository_suite"] == "2605 passed"
    assert "full repository suite must pass" in validation["required_final_validation"]
