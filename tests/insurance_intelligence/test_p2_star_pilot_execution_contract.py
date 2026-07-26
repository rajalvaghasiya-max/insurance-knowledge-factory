import json
from pathlib import Path


CONTRACT_PATH = Path(
    "docs/architecture/insurance_intelligence/"
    "P2_STAR_PILOT_EXECUTION_AND_ACCEPTANCE_CONTRACT.json"
)


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_p2_contract_is_versioned_and_bounded_to_star_pilot():
    contract = _load_contract()

    assert contract["contract_id"] == "p2_star_pilot_execution_and_acceptance_v1"
    assert contract["contract_version"] == "1.0"
    assert contract["phase"] == "P2"
    assert contract["status"] == "PLANNED"
    assert contract["predecessor"]["milestone"] == "MO-023J"
    assert contract["predecessor"]["outcome"] == "PASS"
    assert contract["predecessor"]["closure_commit"] == "bc1d8b4"
    assert contract["initial_next_unit"] == "P2.1"
    assert contract["final_decision"] == "NOT_YET_EVALUATED"


def test_p2_contract_has_exact_ordered_execution_units():
    contract = _load_contract()
    units = contract["execution_units"]
    unit_ids = [unit["unit_id"] for unit in units]

    assert unit_ids == [
        "P2.1",
        "P2.2",
        "P2.3",
        "P2.4",
        "P2.5",
        "P2.6",
        "P2.7",
    ]
    assert contract["execution_order"] == unit_ids

    for unit in units:
        assert unit["name"]
        assert unit["purpose"]
        assert unit["required_artifacts"]
        assert unit["pass_conditions"]
        assert unit["blocked_conditions"]


def test_p2_contract_covers_all_mandatory_hardening_outcomes():
    contract = _load_contract()
    units = {unit["unit_id"]: unit for unit in contract["execution_units"]}

    assert "topic-level completeness" in units["P2.1"]["name"].lower()
    assert "materially different" in units["P2.2"]["name"].lower()
    assert "publication decision" in units["P2.3"]["name"].lower()
    assert "authoritative publication" in units["P2.4"]["name"].lower()
    assert "adversarial" in units["P2.5"]["name"].lower()
    assert "legacy recommendation bypass" in units["P2.6"]["name"].lower()
    assert "certification closure" in units["P2.7"]["name"].lower()


def test_p2_contract_requires_explicit_publication_boundaries():
    contract = _load_contract()
    serialized = json.dumps(contract).lower()

    assert "publish, withhold or blocked" in serialized
    assert "bound_not_published" in serialized
    assert "withheld and blocked rules" in serialized
    assert "cannot be published" in serialized
    assert "no publication record claims or guarantees claim payment" in serialized


def test_p2_contract_requires_critical_adversarial_safety_behavior():
    contract = _load_contract()
    adversarial = next(
        unit for unit in contract["execution_units"] if unit["unit_id"] == "P2.5"
    )
    serialized = json.dumps(adversarial).lower()

    assert "hallucination" in serialized
    assert "scope drift" in serialized
    assert "recommendation leakage" in serialized
    assert "status loss" in serialized
    assert "claim-payment guarantee" in serialized
    assert "all critical safety cases pass" in serialized


def test_p2_contract_blocks_reachable_legacy_recommendation_bypasses():
    contract = _load_contract()
    bypass = next(
        unit for unit in contract["execution_units"] if unit["unit_id"] == "P2.6"
    )
    serialized = json.dumps(bypass).lower()

    assert "removed, routed, blocked or explicitly deferred" in serialized
    assert "no active unclassified bypass path remains" in serialized
    assert "all active recommendation-capable paths route through the governed safety gate" in serialized
    assert "deferred paths are disabled or demonstrably unreachable" in serialized


def test_p2_contract_preserves_scope_boundaries_and_no_claim_guarantee():
    contract = _load_contract()
    excluded = contract["scope_boundaries"]["excluded"]

    assert "Broad insurer or product expansion." in excluded
    assert "Product comparison, ranking or suitability engines." in excluded
    assert "Consumer or advisor UI work." in excluded
    assert "Database migration or scale optimization." in excluded
    assert "Motor, Life or Claims expansion." in excluded
    assert "Any claim-payment guarantee." in excluded


def test_p2_final_pass_requires_every_mandatory_unit_and_full_suite():
    contract = _load_contract()
    closure = next(
        unit for unit in contract["execution_units"] if unit["unit_id"] == "P2.7"
    )
    pass_conditions = " ".join(closure["pass_conditions"])

    assert "P2.1 through P2.6 are PASS." in pass_conditions
    assert "All critical adversarial cases pass." in pass_conditions
    assert "Publication boundaries are proven." in pass_conditions
    assert "No active legacy recommendation bypass remains." in pass_conditions
    assert "Full repository suite passes." in pass_conditions
