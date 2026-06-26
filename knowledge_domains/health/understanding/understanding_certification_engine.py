from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .understanding_asset_models import UnderstandingCertification, stable_id


class UnderstandingCertificationEngine:
    """UACS v1.0 certification engine."""

    REQUIRED_CHECKS = {
        "reality_present": lambda d: bool(d.get("reality")),
        "misunderstanding_present": lambda d: bool(d.get("common_misunderstanding")),
        "root_cause_present": lambda d: bool(d.get("root_causes")),
        "consequence_present": lambda d: bool(d.get("consequence")),
        "example_present": lambda d: bool(d.get("example")),
        "golden_rule_present": lambda d: bool(d.get("golden_rule")),
        "verification_present": lambda d: bool(d.get("verification")),
        "transformation_present": lambda d: bool(d.get("transformation")),
    }

    def certify(self, asset_payload: Dict[str, Any]) -> UnderstandingCertification:
        checks = {name: bool(fn(asset_payload)) for name, fn in self.REQUIRED_CHECKS.items()}
        passed = all(checks.values())
        score = round(sum(1 for v in checks.values() if v) / len(checks) * 100)
        cert_payload = {
            "asset_id": asset_payload.get("asset_id"),
            "concept_id": asset_payload.get("concept_id"),
            "checks": checks,
        }
        return UnderstandingCertification(
            certification_id=stable_id("uac", cert_payload),
            asset_id=str(asset_payload.get("asset_id")),
            concept_id=str(asset_payload.get("concept_id")),
            status="PASS" if passed else "FAIL",
            score=score,
            checks=checks,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
