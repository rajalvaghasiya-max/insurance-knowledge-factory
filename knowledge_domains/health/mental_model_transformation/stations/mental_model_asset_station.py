from __future__ import annotations

from typing import Any, Dict
from ..mental_model_models import MentalModelAsset, stable_hash, utc_now_iso
from ..transformation_blueprint import TransformationBlueprint


class MentalModelAssetStation:
    """Assembles the final Mental Model Asset. No new intelligence is created here."""

    def manufacture(self, blueprint: TransformationBlueprint) -> MentalModelAsset:
        evidence_traceability: Dict[str, Any] = {
            "distillation_report": blueprint.source_distillation_id,
            "observation_id": blueprint.source_observation_id,
            "source_observation": blueprint.source_report.get("observation", {}),
            "relationships": blueprint.source_report.get("relationships", []),
        }
        metrics = {
            "transformation_difficulty": blueprint.knowledge_gap.severity if blueprint.knowledge_gap else "unknown",
            "misconception_strength": blueprint.current_model.confidence if blueprint.current_model else "unknown",
            "transformation_confidence": blueprint.source_report.get("confidence", 0.0),
            "station_count": len(blueprint.station_log),
        }
        draft = {
            "concept_id": blueprint.concept_id,
            "source_distillation_id": blueprint.source_distillation_id,
            "source_observation_id": blueprint.source_observation_id,
            "current_model": blueprint.current_model.belief if blueprint.current_model else None,
            "target_model": blueprint.target_model.belief if blueprint.target_model else None,
        }
        asset_id = stable_hash(draft, prefix="mma")
        return MentalModelAsset(
            asset_id=asset_id,
            concept_id=blueprint.concept_id,
            concept_name=blueprint.concept_name,
            version="1.0",
            current_mental_model=blueprint.current_model,
            target_mental_model=blueprint.target_model,
            knowledge_gap=blueprint.knowledge_gap,
            transformation_plan=blueprint.transformation_plan,
            decision_readiness=blueprint.decision_readiness,
            behaviour_goal=blueprint.behaviour_goal,
            verification=blueprint.verification,
            evidence_traceability=evidence_traceability,
            transformation_metrics=metrics,
            certification_status="pending",
            factory_signature={
                "factory": "PolicyScna Knowledge Factory",
                "production_cell": "MentalModelTransformationCell",
                "version": "1.0",
                "deterministic": True,
                "created_at": utc_now_iso(),
            },
        )
