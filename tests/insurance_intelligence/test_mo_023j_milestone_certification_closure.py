import json
from pathlib import Path


CLOSURE_PATH = Path(
    "docs/architecture/insurance_intelligence/"
    "MO-023J_RULE_CERTIFICATION_MILESTONE_CLOSURE.json"
)


def _record() -> dict:
    return json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))


def test_mo_023j_closure_is_a_bounded_pass_record():
    record = _record()

    assert record["schema_version"] == "1.0"
    assert record["record_type"] == "milestone_certification_closure"
    assert record["milestone_id"] == "MO-023J"
    assert record["certification_outcome"] == "PASS"
    assert record["certified_at_milestone_head"] == "a2f3441"


def test_mo_023j_closure_contains_every_completed_unit_once():
    record = _record()
    units = record["completed_units"]

    assert [unit["unit_id"] for unit in units] == [
        "MO-023J.1",
        "MO-023J.2",
        "MO-023J.3",
        "MO-023J.4",
        "MO-023J.5",
        "P1.7",
    ]
    assert [unit["pull_request"] for unit in units] == [19, 20, 21, 22, 23, 24]
    assert len({unit["merge_reference"] for unit in units}) == len(units)


def test_mo_023j_closure_certifies_three_materially_distinct_cases():
    record = _record()
    cases = record["certified_cases"]

    assert {(case["product_id"], case["topic_id"]) for case in cases} == {
        ("star_comprehensive", "conditional_obligation"),
        ("star_comprehensive", "coverage_limit"),
        ("activ_one", "waiting_period"),
    }
    assert all(case["expected_outcome"] == "PASS" for case in cases)


def test_mo_023j_closure_proves_generic_replication_without_infrastructure_changes():
    record = _record()
    proof = record["generic_reuse_proof"]

    assert proof["contracts_modified_for_replication"] is False
    assert proof["topic_catalogue_modified_for_replication"] is False
    assert proof["completeness_evaluator_modified_for_replication"] is False
    assert proof["certification_runner_modified_for_replication"] is False


def test_mo_023j_closure_preserves_validation_evidence():
    evidence = _record()["validation_evidence"]

    assert evidence == {
        "focused_certification_tests_passed": 58,
        "insurance_intelligence_tests_passed": 1539,
        "full_repository_tests_passed": 2486,
        "validated_milestone_head": "a2f3441",
    }


def test_mo_023j_closure_does_not_authorize_publication_or_claim_payment():
    record = _record()
    boundaries = " ".join(record["governance_boundaries"]).lower()
    decision = record["closure_decision"]

    assert decision["mo_023j_closed"] is True
    assert decision["p1_certification_scope_closed"] is True
    assert decision["ready_to_start_p2"] is True
    assert decision["publication_authorized"] is False
    assert "does not publish" in boundaries
    assert "does not guarantee claim payment" in boundaries
    assert "individual policy instance" in boundaries


def test_mo_023j_closure_defers_p2_work_explicitly():
    deferred = " ".join(_record()["deferred_to_p2"]).lower()

    assert "topic-level completeness" in deferred
    assert "publication" in deferred
    assert "adversarial evaluation" in deferred
    assert "legacy recommendation bypass" in deferred
