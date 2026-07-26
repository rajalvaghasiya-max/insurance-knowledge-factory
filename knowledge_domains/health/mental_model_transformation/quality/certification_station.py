from __future__ import annotations

from typing import Any, Dict
from ..mental_model_models import MentalModelAsset, utc_now_iso


class CertificationStation:
    def certify(self, asset: MentalModelAsset, quality_report: Dict[str, Any]) -> Dict[str, Any]:
        status = "PASS" if quality_report.get("pass") else "FAIL"
        return {
            "certification_id": asset.asset_id.replace("mma_", "mmc_"),
            "asset_id": asset.asset_id,
            "concept_id": asset.concept_id,
            "status": status,
            "checks": quality_report.get("checks", {}),
            "created_at": utc_now_iso(),
        }
