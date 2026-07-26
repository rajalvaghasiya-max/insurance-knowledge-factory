import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .advisor_intelligence_builder import build_advisor_intelligence_asset
from .advisor_intelligence_certification_engine import (
    certify_advisor_intelligence_asset,
)


class AdvisorIntelligenceAssetBuilder:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def build(self, concept_id: str) -> dict:
        asset = build_advisor_intelligence_asset(concept_id)

        asset_id = f"aia_{uuid4().hex[:24]}"
        asset.asset_id = asset_id

        certification = certify_advisor_intelligence_asset(asset)
        asset.certification = certification

        output_dir = (
            self.repo_root
            / "knowledge"
            / "factory"
            / "golden_concepts"
            / concept_id
            / "advisor_intelligence_assets"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        asset_path = output_dir / f"{asset_id}_advisor_intelligence_asset.json"
        certification_path = output_dir / f"{asset_id}_advisor_intelligence_certification.json"
        summary_path = output_dir / "advisor_intelligence_asset_summary.json"

        asset_data = asdict(asset)

        asset_path.write_text(
            json.dumps(asset_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        certification_data = {
            "certification_id": f"aic_{uuid4().hex[:24]}",
            "asset_id": asset_id,
            "concept_id": concept_id,
            "status": certification.status,
            "score": certification.score,
            "passed_checks": certification.passed_checks,
            "failed_checks": certification.failed_checks,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        certification_path.write_text(
            json.dumps(certification_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        summary_data = {
            "production_cell": "AdvisorIntelligenceAssetBuilder",
            "version": "1.0",
            "assets_manufactured": 1,
            "asset": str(asset_path.relative_to(self.repo_root)),
            "certification": str(certification_path.relative_to(self.repo_root)),
            "certification_status": certification.status,
            "score": certification.score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        summary_path.write_text(
            json.dumps(summary_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "asset": str(asset_path),
            "certification": str(certification_path),
            "summary": str(summary_path),
            "status": certification.status,
            "score": certification.score,
        }