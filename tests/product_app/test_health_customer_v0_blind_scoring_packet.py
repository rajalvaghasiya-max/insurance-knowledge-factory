from scripts.build_health_customer_v0_blind_scoring_packet import build_packet


def _artifact(prefix: str) -> dict:
    return {
        "cases": [
            {
                "case_id": "case-1",
                "conversation_id": "conv-1",
                "turn_index": 1,
                "concept_area": "waiting_period",
                "user_text": "What does this mean?",
                "released_text": f"{prefix} answer one",
            },
            {
                "case_id": "case-2",
                "conversation_id": "conv-1",
                "turn_index": 2,
                "concept_area": "waiting_period",
                "user_text": "And then?",
                "released_text": f"{prefix} answer two",
            },
        ]
    }


def test_blind_packet_is_reproducible_and_hides_run_identity() -> None:
    packet_1, reveal_1 = build_packet(_artifact("before"), _artifact("after"), seed=17)
    packet_2, reveal_2 = build_packet(_artifact("before"), _artifact("after"), seed=17)

    assert packet_1 == packet_2
    assert reveal_1 == reveal_2
    assert packet_1["case_count"] == 2
    assert all("BEFORE" not in str(case) and "AFTER" not in str(case) for case in packet_1["cases"])
    assert {row["answer_a"] for row in reveal_1["cases"]} <= {"BEFORE", "AFTER"}


def test_blind_packet_rejects_case_set_drift() -> None:
    before = _artifact("before")
    after = _artifact("after")
    after["cases"].pop()

    try:
        build_packet(before, after, seed=1)
    except ValueError as exc:
        assert "case sets differ" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected case-set mismatch to fail")


def test_blind_packet_rejects_question_drift() -> None:
    before = _artifact("before")
    after = _artifact("after")
    after["cases"][0]["user_text"] = "Changed question"

    try:
        build_packet(before, after, seed=1)
    except ValueError as exc:
        assert "user_text changed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected question drift to fail")
