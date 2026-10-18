from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path("benchmarks/health_customer_v0")
MANIFEST_PATH = ROOT / "dev_benchmark_36_v1.json"
REFERENCE_KEYS = {
    "must_include",
    "legitimate_dependency",
    "must_not_imply",
    "acceptable_clarification",
    "unnecessary_deferral",
}
EXPECTED_ROUTES = {
    "pre_existing_disease": (
        "health:concept:pre_existing_disease",
        "pre_existing_disease",
    ),
    "waiting_period": ("health:concept:waiting_period", "waiting_period"),
    "restoration": ("health:concept:restoration", "restoration"),
    "room_rent_limit": ("health:concept:room_rent_limit", "room_rent_limit"),
    "bariatric_surgery": (
        "health:concept:bariatric_surgery",
        "bariatric_surgery",
    ),
    "copayment": ("health:concept:copayment", "conditional_copayment"),
}


def _load() -> tuple[dict, list[dict]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    cases: list[dict] = []
    for relative in manifest["conversation_files"]:
        payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.0"
        assert payload["conversation_id"]
        assert all(
            case["conversation_id"] == payload["conversation_id"]
            for case in payload["cases"]
        )
        cases.extend(payload["cases"])
    return manifest, cases


def _all_strings(value: object) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(_all_strings(item))
        return result
    if isinstance(value, dict):
        result: set[str] = set()
        for item in value.values():
            result.update(_all_strings(item))
        return result
    return set()


def test_dev_benchmark_36_is_preregistered_and_structurally_complete() -> None:
    manifest, cases = _load()

    assert manifest["benchmark_role"] == "DEV_ONLY"
    assert manifest["holdout_eligible"] is False
    assert manifest["preregistered_before_first_run"] is True
    assert manifest["case_count"] == 36
    assert manifest["conversation_count"] == 12
    assert manifest["multi_turn_conversation_count"] == 12
    assert len(manifest["conversation_files"]) == 12
    assert len(cases) == 36

    case_ids = [case["case_id"] for case in cases]
    questions = [case["user_text"] for case in cases]
    assert len(case_ids) == len(set(case_ids))
    assert len(questions) == len(set(questions))

    concept_counts = Counter(case["concept_area"] for case in cases)
    assert concept_counts == Counter({concept: 6 for concept in EXPECTED_ROUTES})

    conversation_counts = Counter(case["conversation_id"] for case in cases)
    assert set(conversation_counts.values()) == {3}

    for conversation_id in conversation_counts:
        turns = sorted(
            (case for case in cases if case["conversation_id"] == conversation_id),
            key=lambda case: case["turn_index"],
        )
        assert [case["turn_index"] for case in turns] == [1, 2, 3]
        assert [case["prior_context_required"] for case in turns] == [False, True, True]

    for case in cases:
        assert isinstance(case["user_text"], str) and case["user_text"].strip()
        expected_concept_id, expected_topic = EXPECTED_ROUTES[case["concept_area"]]
        assert case["expected_concept_id"] == expected_concept_id
        assert case["expected_topic"] == expected_topic

        reference = case["reference"]
        assert set(reference) == REFERENCE_KEYS
        for key in REFERENCE_KEYS:
            assert isinstance(reference[key], list)
            assert reference[key]
            assert all(isinstance(item, str) and item.strip() for item in reference[key])

        assert set(case["evaluation"]) == {"primary_origin", "secondary_tags"}
        assert case["evaluation"]["primary_origin"] is None
        assert case["evaluation"]["secondary_tags"] == []


def test_restoration_dev_questions_do_not_reuse_exact_frozen_pack_text() -> None:
    _, cases = _load()
    frozen = json.loads(
        Path("benchmarks/gsi_p1/frozen_restoration_blind_pack_v1.json").read_text(
            encoding="utf-8"
        )
    )
    frozen_strings = _all_strings(frozen)
    restoration_questions = {
        case["user_text"] for case in cases if case["concept_area"] == "restoration"
    }
    assert restoration_questions.isdisjoint(frozen_strings)
