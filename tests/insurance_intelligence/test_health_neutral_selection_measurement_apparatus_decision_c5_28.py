import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/architecture/health_neutral_selection_measurement_apparatus_decision_c5_28_2026-08-26.json"
AUTH = ROOT / "docs/architecture/health_eligible_universe_preregistration_authorization_v1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_measurement_apparatus_decision_replaces_runtime_autonomous_proof_assumption():
    record = _load(DECISION)
    assert record["architecture_verdict"] == "AUTONOMOUS_RUNTIME_ELIGIBILITY_PROOF_NOT_REQUIRED_FOR_NEUTRAL_REPEATABILITY_TEST"
    assert record["decision"] == "GOVERNED_PREREGISTERED_ELIGIBLE_UNIVERSE_IS_SUFFICIENT_FOR_NEUTRAL_REPEATABILITY_SELECTION"
    assert record["product14_authorized"] is False


def test_c5_24_runtime_source_firewall_is_preserved():
    record = _load(DECISION)
    assert "C5.24 semantic-bearing filed product documents are not runtime preselection metadata by post-parse field filtering" in record["does_not_supersede"]
    assert "raw semantic-bearing content does not cross into the selector" in record["three_stage_apparatus"]["stage_2_eligible_universe_certification"]["requirements"]


def test_universe_certification_is_exhaustive_and_target_semantics_cannot_drive_membership():
    record = _load(DECISION)
    requirements = record["three_stage_apparatus"]["stage_2_eligible_universe_certification"]["requirements"]
    assert "every candidate in the preregistered pool is adjudicated; no stop-at-first behavior" in requirements
    assert "membership may depend only on frozen eligibility predicates" in requirements
    assert "target-clause presence, target-clause content, semantic complexity and semantic-fit information cannot affect membership" in requirements


def test_selector_sees_only_frozen_opaque_eligible_ids_and_has_no_override():
    record = _load(DECISION)
    requirements = record["three_stage_apparatus"]["stage_3_deterministic_blind_selection"]["requirements"]
    assert "eligible-universe artifact hash frozen before selection" in requirements
    assert "selector sees only opaque eligible identifiers plus the minimum preregistered deterministic ordering/selection inputs" in requirements
    assert "no product substitution or selection override after selection" in requirements


def test_stop_rule_prevents_automatic_product15_or_selector_field_extension():
    record = _load(DECISION)
    stop = record["stop_rule"]
    assert stop["statement"] == "Product #14 is the final experiment in the current neutral-selection hardening cycle."
    assert "A Product #14 failure may not automatically authorize Product #15 or another selector-field repair." in stop["justification"]
    assert stop["failure_routing"]["ELIGIBLE_UNIVERSE_CERTIFICATION_INTEGRITY_FALSIFIED"] == "repair certification governance; do not extend runtime selector"


def test_next_authorization_is_preregistration_only():
    auth = _load(AUTH)
    assert auth["authorized_next_action"] == "HEALTH_GOVERNED_ELIGIBLE_UNIVERSE_PREREGISTRATION_ONLY"
    assert "construct or certify the eligible universe before preregistration is merged" in auth["not_authorized"]
    assert "select Product #14" in auth["not_authorized"]
    assert auth["product14_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    assert auth["runtime_change_authorized"] is False
    assert auth["motor_authorized"] is False
