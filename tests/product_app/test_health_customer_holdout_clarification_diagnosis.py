from __future__ import annotations

import json
from pathlib import Path

from scripts.diagnose_health_customer_v0_holdout_clarifications import build_diagnosis


def test_diagnosis_redacts_text_and_classifies_known_fallbacks(tmp_path: Path) -> None:
    run = {
        "cases": [
            {
                "case_id": "c1",
                "answer_status": "CLARIFICATION",
                "selected_concept_id": None,
                "selected_topic": None,
                "render_outcome": "PASS",
                "released_text": "I could not understand the insurance concept confidently enough to answer safely. Please rephrase the question or name the insurance term you want explained.",
            },
            {
                "case_id": "c2",
                "answer_status": "CLARIFICATION",
                "selected_concept_id": "health:concept:copayment",
                "selected_topic": "copayment",
                "render_outcome": "PASS",
                "released_text": "I understand the insurance topic, but the specific part of the question is ambiguous across insurance concepts. Please rephrase what you want to know about this term.",
            },
        ]
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run), encoding="utf-8")

    diagnosis = build_diagnosis(path)

    assert diagnosis["case_count"] == 2
    assert diagnosis["selected_concept_count"] == 1
    assert diagnosis["clarification_reason_counts"] == {
        "cross_concept_component_rejected": 1,
        "semantic_interpretation_clarification": 1,
    }
    assert all("released_text" not in row for row in diagnosis["cases"])
