from .decision_intelligence_models import (
    DecisionIntelligenceAsset,
    DecisionIntelligenceCertification,
)


def certify_decision_intelligence_asset(
    asset: DecisionIntelligenceAsset,
) -> DecisionIntelligenceCertification:
    """
    Certify a Decision Intelligence Asset.

    A Decision Intelligence Asset is considered complete only if all
    mandatory decision-support components are present.
    """

    passed_checks: list[str] = []
    failed_checks: list[str] = []

    checks = {
        "decision_context": asset.decision_context is not None,
        "decision_options": bool(asset.decision_options),
        "tradeoff_analysis": asset.tradeoff_analysis is not None,
        "assumptions": bool(asset.assumptions),
        "financial_implications": bool(asset.financial_implications),
        "advisor_considerations": bool(asset.advisor_considerations),
        "decision_readiness": asset.decision_readiness is not None,
        "recommended_next_questions": bool(asset.recommended_next_questions),
        "warning_signals": bool(asset.warning_signals),
        "verification": asset.verification is not None,
        "source_assets": bool(asset.source_assets),
    }

    for check_name, passed in checks.items():
        if passed:
            passed_checks.append(check_name)
        else:
            failed_checks.append(check_name)

    score = int((len(passed_checks) / len(checks)) * 100)

    status = "PASS" if not failed_checks else "FAIL"

    return DecisionIntelligenceCertification(
        status=status,
        score=score,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
    )