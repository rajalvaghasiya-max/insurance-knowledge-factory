from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .mental_model_models import stable_json_dumps, utc_now_iso
from .stations.incoming_inspection_station import IncomingInspectionStation
from .stations.current_model_detection_station import CurrentModelDetectionStation
from .stations.target_model_station import TargetModelStation
from .stations.knowledge_gap_station import KnowledgeGapStation
from .stations.transformation_planning_station import TransformationPlanningStation
from .stations.decision_readiness_station import DecisionReadinessStation
from .stations.behaviour_goal_station import BehaviourGoalStation
from .stations.verification_station import VerificationStation
from .stations.mental_model_asset_station import MentalModelAssetStation
from .quality.quality_station import QualityStation
from .quality.certification_station import CertificationStation


class MentalModelTransformationLine:
    def __init__(self, output_root: str | Path = "knowledge/factory/mental_models") -> None:
        self.output_root = Path(output_root)
        self.inspector = IncomingInspectionStation()
        self.current_station = CurrentModelDetectionStation()
        self.target_station = TargetModelStation()
        self.gap_station = KnowledgeGapStation()
        self.plan_station = TransformationPlanningStation()
        self.readiness_station = DecisionReadinessStation()
        self.behaviour_station = BehaviourGoalStation()
        self.verification_station = VerificationStation()
        self.asset_station = MentalModelAssetStation()
        self.quality_station = QualityStation()
        self.certification_station = CertificationStation()

    def manufacture_from_report(self, report: Dict[str, Any]) -> Optional[Dict[str, Path]]:
        blueprint = self.inspector.manufacture(report)
        if not blueprint.inspection.get("pass"):
            return None

        blueprint = self.current_station.manufacture(blueprint)
        blueprint = self.target_station.manufacture(blueprint)
        blueprint = self.gap_station.manufacture(blueprint)
        blueprint = self.plan_station.manufacture(blueprint)
        blueprint = self.readiness_station.manufacture(blueprint)
        blueprint = self.behaviour_station.manufacture(blueprint)
        blueprint = self.verification_station.manufacture(blueprint)
        asset = self.asset_station.manufacture(blueprint)
        quality = self.quality_station.inspect(asset)
        certification = self.certification_station.certify(asset, quality)

        # Update exported certification status without mutating dataclass internals by dict export.
        asset_dict = asset.to_dict()
        asset_dict["certification_status"] = certification["status"]

        concept_dir = self.output_root / blueprint.concept_id
        concept_dir.mkdir(parents=True, exist_ok=True)
        stem = asset.asset_id
        paths = {
            "blueprint": concept_dir / f"{stem}_transformation_blueprint.json",
            "asset": concept_dir / f"{stem}_mental_model_asset.json",
            "quality": concept_dir / f"{stem}_quality_report.json",
            "certification": concept_dir / f"{stem}_certification.json",
            "event": concept_dir / f"{stem}_event.json",
        }
        event = {
            "event_type": "mental_model_asset_manufactured",
            "asset_id": asset.asset_id,
            "concept_id": asset.concept_id,
            "source_distillation_id": blueprint.source_distillation_id,
            "status": certification["status"],
            "created_at": utc_now_iso(),
        }
        writes = {
            "blueprint": blueprint.to_dict(),
            "asset": asset_dict,
            "quality": quality,
            "certification": certification,
            "event": event,
        }
        for key, path in paths.items():
            path.write_text(stable_json_dumps(writes[key]), encoding="utf-8")
        return paths

    def run_from_reports_dir(self, reports_dir: str | Path) -> Dict[str, Any]:
        reports_dir = Path(reports_dir)
        outputs: List[Dict[str, str]] = []
        considered = 0
        for path in sorted(reports_dir.glob("*_distillation_report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            considered += 1
            result = self.manufacture_from_report(report)
            if result:
                outputs.append({k: str(v) for k, v in result.items()})
        summary = {
            "production_line": "Mental Model Transformation Line",
            "version": "1.0",
            "reports_considered": considered,
            "assets_manufactured": len(outputs),
            "outputs": outputs,
            "created_at": utc_now_iso(),
        }
        summary_path = self.output_root / "mental_model_transformation_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(stable_json_dumps(summary), encoding="utf-8")
        summary["summary_path"] = str(summary_path)
        return summary
