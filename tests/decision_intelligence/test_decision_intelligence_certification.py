from knowledge_factory.decision_intelligence.decision_intelligence_builder import (
    build_decision_intelligence_asset,
)

from knowledge_factory.decision_intelligence.decision_intelligence_certification_engine import (
    certify_decision_intelligence_asset,
)


def test_decision_intelligence_certification_passes():
    asset = build_decision_intelligence_asset("copay")

    certification = certify_decision_intelligence_asset(asset)

    assert certification.status == "PASS"
    assert certification.score == 100
    assert certification.failed_checks == []