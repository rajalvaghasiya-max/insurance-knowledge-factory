from __future__ import annotations

import json
from pathlib import Path

from scripts.build_health_customer_v0_holdout_scorer_packet import build_packet


def test_holdout_scorer_packet_exposes_only_scoring_fields(tmp_path: Path) -> None:
    run = {
        "benchmark_id": "health-customer-v0-independent-holdout-v2",
        "cases": [
            {
                "case_id": "c1",
                "conversation_id": "conv1",
                "turn_index": 1,
                "prior_context_required": False,
                "concept_area": "copayment",
                "user_text": "What does co-pay mean?",
                "released_text": "A co-pay is the share you pay.",
                "reference": {
                    "must_include": ["Explain co-pay."],
                    "legitimate_dependency": ["Exact percentage depends on the policy."],
                    "must_not_imply": ["Do not invent a percentage."],
                    "acceptable_clarification": ["Ask for policy only for exact application."],
                    "unnecessary_deferral": ["General explanation can be given now."],
                },
                "answer_status": "CLARIFICATION",
                "selected_concept_id": "health:concept:copayment",
                "selected_topic": "copayment",
                "render_outcome": "PASS",
                "context_turn_count_before": 0,
                "context_turn_count_after": 1,
                "quality_scoring": "NOT_SCORED",
            }
        ],
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run), encoding="utf-8")

    packet = build_packet(path)

    assert packet["benchmark_role"] == "HOLDOUT_SCORER_PACKET"
    assert packet["case_count"] == 1
    case = packet["cases"][0]
    assert set(case) == {
        "case_id",
        "conversation_id",
        "turn_index",
        "prior_context_required",
        "concept_area",
        "user_text",
        "released_text",
        "reference",
    }
    assert "answer_status" not in case
    assert "selected_concept_id" not in case
    assert "render_outcome" not in case
