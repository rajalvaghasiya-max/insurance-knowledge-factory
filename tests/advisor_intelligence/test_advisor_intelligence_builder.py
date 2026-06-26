from knowledge_factory.advisor_intelligence.advisor_intelligence_builder import (
    build_advisor_intelligence_asset,
)


def test_advisor_intelligence_builder_creates_copay_asset():
    asset = build_advisor_intelligence_asset("copay")

    assert asset.concept_id == "copay"
    assert asset.concept_name == "Copay"
    assert asset.version == "1.0"

    assert asset.customer_psychology.visible_focus == "lower premium"
    assert asset.customer_psychology.blind_spot == "claim-stage liability"

    assert "present_bias" in asset.decision_psychology.biases
    assert asset.decision_psychology.decision_pattern == "save now, pay later"

    assert asset.advisor_confidence.ready_to_explain is True
    assert asset.certification.status == "PENDING"


def test_advisor_intelligence_builder_rejects_unsupported_concept():
    try:
        build_advisor_intelligence_asset("waiting_period")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unsupported concept_id" in str(exc)