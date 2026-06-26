from knowledge_factory.decision_intelligence.decision_intelligence_builder import (
    build_decision_intelligence_asset,
)


def test_builder_creates_copay_asset():

    asset = build_decision_intelligence_asset("copay")

    assert asset.concept_id == "copay"
    assert asset.concept_name == "Copay"

    assert len(asset.decision_options) == 2

    assert asset.decision_readiness.overall == "READY"

    assert asset.certification.status == "PENDING"


def test_builder_rejects_unknown_concept():

    try:
        build_decision_intelligence_asset("abc")
        assert False
    except ValueError:
        pass