import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .decision_intelligence_builder import (
    build_decision_intelligence_asset,
)
from .decision_intelligence_certification_engine import (
    certify_decision_intelligence_asset,
)


class DecisionIntelligenceAssetBuilder:

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def build(self, concept_id: str) -> dict:

        asset = build_decision_intelligence_asset(concept_id)

        asset_id = f"dia_{uuid4().hex[:24]}"
        asset.asset_id = asset_id

        certification = certify_decision_intelligence_asset(asset)
        asset.certification = certification

        output_dir = (
            self.repo_root
            / "knowledge"
            / "factory"
            / "golden_concepts"
            / concept_id
            / "decision_intelligence_assets"
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        asset_path = (
            output_dir
            / f"{asset_id}_decision_intelligence_asset.json"
        )

        certification_path = (
            output_dir
            / f"{asset_id}_decision_intelligence_certification.json"
        )

        summary_path = (
            output_dir
            / "decision_intelligence_asset_summary.json"
        )

        asset_path.write_text(
            json.dumps(
                asdict(asset),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        certification_json = {
            "certification_id": f"dic_{uuid4().hex[:24]}",
            "asset_id": asset_id,
            "concept_id": concept_id,
            "status": certification.status,
            "score": certification.score,
            "passed_checks": certification.passed_checks,
            "failed_checks": certification.failed_checks,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        certification_path.write_text(
            json.dumps(
                certification_json,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        summary = {
            "production_cell": "DecisionIntelligenceAssetBuilder",
            "version": "1.0",
            "assets_manufactured": 1,
            "asset": str(asset_path.relative_to(self.repo_root)),
            "certification": str(
                certification_path.relative_to(self.repo_root)
            ),
            "certification_status": certification.status,
            "score": certification.score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        summary_path.write_text(
            json.dumps(
                summary,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "asset": str(asset_path),
            "certification": str(certification_path),
            "summary": str(summary_path),
            "status": certification.status,
            "score": certification.score,
        }