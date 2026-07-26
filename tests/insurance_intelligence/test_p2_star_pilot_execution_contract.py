import json
from pathlib import Path


CONTRACT_PATH = Path(
    "docs/architecture/insurance_intelligence/"
    "P2_STAR_PILOT_EXECUTION_AND_ACCEPTANCE_CONTRACT.json"
)


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_p2_contract_is_versioned_and_separates_generic_and_pilot_decisions():
    contract = _load_contract()

    assert contract["contract_id"] == "p2_generic_hardening_with_star_pilot_v2"
    assert contract["contract_version"] == "2.0"
    assert contract["phase"] == "P2"
    assert contract["status"] == "PLANNED"
    assert contract["predecessor"]["milestone"] == "MO-023J"
    assert contract["predecessor"]["outcome"] == "PASS"
    assert contract["predecessor"]["closure_commit"] == "bc1d8b4"
    assert contract["initial_next_unit"] == "P2.1"
    assert contract["generic_capability_decision"] == "NOT_YET_EVALUATED"
    assert contract["star_pilot_decision"] == "NOT_YET_EVALUATED"


def test_p2_contract_has_exact_ordered_execution_units_and_two_layers():
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
        assert unit["generic_capability"]["deliverables"]
        assert unit["generic_capability"]["pass_conditions"]
        assert unit["pilot_proof"]["product"] == "Star Comprehensive"
        assert unit["pilot_proof"]["deliverables"]
        assert unit["pilot_proof"]["pass_conditions"]
        assert unit["blocked_conditions"]


def test_p2_architecture_principle_requires_generic_first_and_star_only_as_proof():
    contract = _load_contract()
    principle = contract["architecture_principle"].lower()
    separation = json.dumps(contract["separation_rules"]).lower()

    assert "reusable generic capability" in principle
    assert "star comprehensive as the bounded pilot" in principle
    assert "generic contracts, evaluators, runners and decision logic" in principle
    assert "must not depend on star identifiers or semantics" in principle
    assert "generic code must not import star-specific fixtures" in separation
    assert "star pilot proof must invoke the generic layer" in separation
    assert "pilot-specific limitations cannot weaken" in separation


def test_every_unit_defines_reusable_generic_capability_not_star_infrastructure():
    contract = _load_contract()

    for unit in contract["execution_units"]:
        generic = json.dumps(unit["generic_capability"]).lower()
        assert "star comprehensive" not in generic
        assert "star-specific" not in generic or "no new product-specific" in generic

    serialized = json.dumps(contract).lower()
    assert "generic profile validator" in serialized
    assert "publication-decision contract" in serialized
    assert "authoritative-publication contract" in serialized
    assert "generic adversarial-case catalogue contract" in serialized
    assert "bypass-inventory and disposition contract" in serialized


def test_p2_contract_covers_all_mandatory_generic_hardening_outcomes():
    contract = _load_contract()
    units = {unit["unit_id"]: unit for unit in contract["execution_units"]}

    assert "topic-profile" in units["P2.1"]["name"].lower()
    assert "rule-certification reuse" in units["P2.2"]["name"].lower()
    assert "publication-decision capability" in units["P2.3"]["name"].lower()
    assert "authoritative-publication capability" in units["P2.4"]["name"].lower()
    assert "adversarial-evaluation capability" in units["P2.5"]["name"].lower()
    assert "bypass inventory and control" in units["P2.6"]["name"].lower()
    assert "generic hardening and star pilot certification closure" in units["P2.7"]["name"].lower()


def test_publication_capabilities_are_generic_and_star_records_are_only_proof():
    contract = _load_contract()
    units = {unit["unit_id"]: unit for unit in contract["execution_units"]}
    decision = json.dumps(units["P2.3"]).lower()
    publication = json.dumps(units["P2.4"]).lower()

    assert "supporting publish, withhold and blocked" in decision
    assert "bound_not_published" in decision
    assert "accepts any governed subject reference" in decision
    assert "publication cannot occur without an approved publish decision" in publication
    assert "reusable across products and topics" in publication
    assert "no star publication record claims or guarantees claim payment" in publication


def test_adversarial_capability_is_generic_with_separate_star_dataset():
    contract = _load_contract()
    adversarial = next(
        unit for unit in contract["execution_units"] if unit["unit_id"] == "P2.5"
    )
    generic = json.dumps(adversarial["generic_capability"]).lower()
    pilot = json.dumps(adversarial["pilot_proof"]).lower()

    assert "hallucination" in generic
    assert "scope drift" in generic
    assert "recommendation leakage" in generic
    assert "status loss" in generic
    assert "claim-payment guarantee" in generic
    assert "non-star catalogue without code modification" in generic
    assert "versioned star adversarial case catalogue" in pilot
    assert "all critical star safety cases pass" in pilot


def test_bypass_control_is_generic_with_star_reachability_proof():
    contract = _load_contract()
    bypass = next(
        unit for unit in contract["execution_units"] if unit["unit_id"] == "P2.6"
    )
    generic = json.dumps(bypass["generic_capability"]).lower()
    pilot = json.dumps(bypass["pilot_proof"]).lower()

    assert "removed, routed, blocked or explicitly deferred" in generic
    assert "all active recommendation-capable paths route through the governed safety gate" in generic
    assert "deferred paths must be disabled or demonstrably unreachable" in generic
    assert "star pilot reachability view" in pilot
    assert "no active unclassified bypass path remains reachable" in pilot


def test_p2_contract_preserves_scope_boundaries_and_no_claim_guarantee():
    contract = _load_contract()
    included = contract["scope_boundaries"]["included"]
    excluded = contract["scope_boundaries"]["excluded"]

    assert "Generic topic-profile, publication-governance, adversarial-evaluation and bypass-control capabilities." in included
    assert "Star Comprehensive as the first bounded pilot proof only." in included
    assert "Broad insurer or product expansion." in excluded
    assert "Product comparison, ranking or suitability engines." in excluded
    assert "Consumer or advisor UI work." in excluded
    assert "Database migration or scale optimization." in excluded
    assert "Motor, Life or Claims expansion." in excluded
    assert "Any claim-payment guarantee." in excluded


def test_p2_final_closure_requires_separate_generic_and_star_passes():
    contract = _load_contract()
    closure = next(
        unit for unit in contract["execution_units"] if unit["unit_id"] == "P2.7"
    )
    generic_pass = " ".join(closure["generic_capability"]["pass_conditions"])
    pilot_pass = " ".join(closure["pilot_proof"]["pass_conditions"])

    assert "All mandatory generic capability deliverables from P2.1 through P2.6 are PASS." in generic_pass
    assert "No generic contract, evaluator, runner, decision gate or control depends on Star identifiers or semantics." in generic_pass
    assert "Cross-product reuse is demonstrated" in generic_pass
    assert "All Star pilot proofs from P2.1 through P2.6 are PASS." in pilot_pass
    assert "All critical Star adversarial cases pass." in pilot_pass
    assert "Star publication boundaries are proven." in pilot_pass
    assert "No active legacy recommendation bypass remains reachable in the Star pilot." in pilot_pass
    assert "The full repository suite passes." in pilot_pass
