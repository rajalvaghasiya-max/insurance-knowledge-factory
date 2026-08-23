from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_post_product4_review_freezes_architecture_without_overclaiming_repeatability() -> None:
    review = _load(
        "docs/architecture/health_foundation_post_product4_repeatability_review_2026-08-23.json"
    )

    assert review["verified_git_diff_observation"]["frozen_runtime_files_changed"] == 0
    assert review["verified_git_diff_observation"]["frozen_runtime_loc_delta"] == 0
    assert review["freeze_decision"]["health_architecture_status"] == "FREEZE_FOUNDATION_ARCHITECTURE_V1"
    assert review["freeze_decision"]["repeatability_claim_status"] == "DO_NOT_CLAIM_FORMALLY_PROVEN"
    assert review["product4"]["protocol_outcome"] == "REPEATABILITY_INCONCLUSIVE"


def test_v2_rubric_distinguishes_schema_instance_reuse_from_new_declarative_shape() -> None:
    protocol = _load("docs/architecture/health_repeatability_test_protocol_v2.json")

    reuse = protocol["classification_rubric"]["REUSE"]["rule"]
    config_spec = protocol["classification_rubric"]["CONFIG_SPEC"]["rule"]

    assert "New product-specific source/evidence records and new instances" in reuse
    assert "No new semantic/spec schema" in reuse
    assert "new governed declarative semantic/spec structural shape" in config_spec
    assert protocol["retroactive_rescoring_authorized"] is False


def test_v2_keeps_runtime_in_exile_and_knowledge_gap_anti_gaming_guards() -> None:
    protocol = _load("docs/architecture/health_repeatability_test_protocol_v2.json")

    rules = "\n".join(protocol["anti_gaming_rules"])
    assert "runtime-in-exile" in rules
    assert "No KNOWLEDGE_GAP may be converted" in rules
    assert protocol["freeze"]["runtime_change_allowed_during_initial_attempt"] is False
    assert protocol["freeze"]["decision_logic_in_config_is_failure"] is True


def test_v2_success_bar_requires_real_reuse_and_preserves_inconclusive_outcome() -> None:
    protocol = _load("docs/architecture/health_repeatability_test_protocol_v2.json")
    bar = protocol["success_bar"]

    assert "Both target concepts are REUSE" in bar["STRONG_REPEATABILITY_PROVEN"]
    assert "at least one is REUSE" in bar["MINIMUM_REPEATABILITY_PROVEN"]
    assert "both scoreable concepts are CONFIG_SPEC with zero REUSE" in bar["REPEATABILITY_NOT_PROVEN"]
    assert "KNOWLEDGE_GAP" in bar["REPEATABILITY_INCONCLUSIVE"]
