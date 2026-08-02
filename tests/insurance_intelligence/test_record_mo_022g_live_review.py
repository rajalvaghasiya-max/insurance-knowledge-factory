import json

from scripts.record_mo_022g_live_review import main


def _evidence():
    return {
        "evidence_id": "live-certification-evidence-test",
        "source_artifact_sha256": "a" * 64,
        "contract_id": "contract-star-comprehensive-conditional-copay-v1",
        "certification_effect": "NONE",
        "certification_granted": False,
        "reviewer_decision": "PENDING",
        "hard_failure_codes": [],
        "unresolved_component_ids": [],
        "routing_reason_codes": ["LOW_EXTRACTION_CONFIDENCE", "RULE_FAMILY_NOT_CERTIFIED"],
        "components": [
            {"component_id": "entry-age-trigger", "status": "MATCHED"},
            {"component_id": "copay-effect", "status": "MATCHED"},
            {"component_id": "continuous-renewal-exception", "status": "MATCHED"},
            {"component_id": "applicability-scope", "status": "MATCHED"},
        ],
    }


def test_cli_records_approval_without_granting_certification(tmp_path):
    source = tmp_path / "evidence.json"
    output = tmp_path / "review.json"
    source.write_text(json.dumps(_evidence()), encoding="utf-8")

    result = main([
        "--input", str(source),
        "--output", str(output),
        "--reviewer-id", "reviewer-1",
        "--reviewed-at", "2026-08-02T05:00:00+00:00",
        "--decision", "APPROVED_FOR_CERTIFICATION_CONSIDERATION",
        "--rationale", "All canonical components match; confidence exception acknowledged.",
    ])

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["decision"] == "APPROVED_FOR_CERTIFICATION_CONSIDERATION"
    assert payload["certification_effect"] == "NONE"
    assert payload["certification_granted"] is False
    assert payload["reviewed_component_ids"] == [
        "applicability-scope",
        "continuous-renewal-exception",
        "copay-effect",
        "entry-age-trigger",
    ]


def test_cli_records_rework_decision(tmp_path):
    source = tmp_path / "evidence.json"
    output = tmp_path / "review.json"
    source.write_text(json.dumps(_evidence()), encoding="utf-8")

    assert main([
        "--input", str(source),
        "--output", str(output),
        "--reviewer-id", "reviewer-2",
        "--decision", "REWORK_REQUIRED",
        "--rationale", "Collect more controlled live samples.",
    ]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["decision"] == "REWORK_REQUIRED"
    assert payload["certification_granted"] is False
