from knowledge_factory.advisor_intelligence.advisor_intelligence_builder import (
    build_advisor_intelligence_asset,
)

from knowledge_factory.advisor_intelligence.advisor_intelligence_certification_engine import (
    certify_advisor_intelligence_asset,
)


def test_advisor_intelligence_certification_passes():
    asset = build_advisor_intelligence_asset("copay")

    certification = certify_advisor_intelligence_asset(asset)

    assert certification.status == "PASS"
    assert certification.score == 100
    assert not certification.failed_checks