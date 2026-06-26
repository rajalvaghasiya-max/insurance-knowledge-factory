from .advisor_intelligence_models import (
    AdvisorIntelligenceAsset,
    AdvisorIntelligenceCertification,
)


def certify_advisor_intelligence_asset(
    asset: AdvisorIntelligenceAsset,
) -> AdvisorIntelligenceCertification:
    passed_checks: list[str] = []
    failed_checks: list[str] = []

    checks = {
        "customer_psychology": asset.customer_psychology is not None,
        "decision_psychology": asset.decision_psychology is not None,
        "common_objections": bool(asset.common_objections),
        "advisor_objective": bool(asset.advisor_objective),
        "response_pattern": bool(asset.response_pattern),
        "storytelling_asset": asset.storytelling_asset is not None,
        "trust_builders": bool(asset.trust_builders),
        "warning_signals": bool(asset.warning_signals),
        "verification": asset.verification is not None,
        "advisor_checklist": bool(asset.advisor_checklist),
        "advisor_confidence": asset.advisor_confidence is not None,
        "source_assets": bool(asset.source_assets),
    }

    for check_name, passed in checks.items():
        if passed:
            passed_checks.append(check_name)
        else:
            failed_checks.append(check_name)

    status = "PASS" if not failed_checks else "FAIL"
    score = int((len(passed_checks) / len(checks)) * 100)

    return AdvisorIntelligenceCertification(
        status=status,
        score=score,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
    )