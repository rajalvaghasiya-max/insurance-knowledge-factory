from knowledge_domains.health.mental_model_transformation.mental_model_transformation_line import (
    MentalModelTransformationLine,
)


def test_waiting_period_profile_drives_mmtc_asset(tmp_path):
    report = {
        "distillation_id": "kdr_waiting_period_test",
        "observation": {
            "observation_id": "WAITING-PERIOD-TEST-001",
            "concept_id": "waiting_period",
            "title": "Customer assumes every health claim is covered from day one",
            "observation": (
                "A customer may assume that buying a health policy means every "
                "illness-related hospitalization is immediately covered."
            ),
            "confidence": "high",
            "source": "advisor_experience",
        },
        "manufacturing_opportunities": [
            {
                "asset_type": "mental_model_asset",
                "reason": "Customer needs a correct waiting-period model.",
                "priority": "high",
                "target_department": "MMTS",
            }
        ],
        "relationships": [
            "waiting_period",
            "claim_date",
            "policy_start_date",
        ],
    }

    outputs = MentalModelTransformationLine(
        output_root=tmp_path / "mental_models"
    ).manufacture_from_report(report)

    assert outputs is not None

    asset_text = outputs["asset"].read_text(encoding="utf-8").lower()

    assert '"concept_id": "waiting_period"' in asset_text
    assert "coverage is not universally active from day one" in asset_text
    assert "waiting periods can be different" in asset_text
    assert "copay" not in asset_text