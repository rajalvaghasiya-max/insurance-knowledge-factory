from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from .package_models import AssetRecord

from knowledge_factory.shared.asset_normalizer import (
    extract_certification_status,
)

class AssetDiscoveryEngine:
    """Discovers latest known assets for a concept across the Factory.

    This is intentionally filesystem-based for v1.0 so it can run in the local
    repository without a database.
    """

    ASSET_PATTERNS = {
        "knowledge_asset": [
            "knowledge/factory/knowledge/{concept}/**/*knowledge_asset*.json",
            "knowledge/factory/golden_concepts/{concept}/**/*knowledge_asset*.json",
        ],
        "understanding_asset": [
            "knowledge/factory/golden_concepts/{concept}/understanding_assets/**/*understanding_asset*.json",
            "knowledge/factory/understanding/{concept}/**/*understanding_asset*.json",
        ],
        "mental_model_asset": [
            "knowledge/factory/mental_models/{concept}/**/*mental_model_asset.json",
            "knowledge/factory/golden_concepts/mental_models/{concept}/**/*mental_model_asset.json",
            "knowledge/factory/golden_concepts/{concept}/mental_models/**/*mental_model_asset.json",
        ],
        "financial_outcome_asset": [
            "knowledge/factory/financial_outcomes/{concept}/**/*financial_outcome_asset.json",
            "knowledge/factory/golden_concepts/financial_outcomes/{concept}/**/*financial_outcome_asset.json",
        ],
        "advisor_intelligence_asset": [
        "knowledge/factory/advisor_intelligence/{concept}/**/*advisor_intelligence_asset.json",
        "knowledge/factory/golden_concepts/{concept}/advisor_intelligence_assets/**/*advisor_intelligence_asset.json",
        "knowledge/factory/golden_concepts/{concept}/advisor_intelligence/**/*advisor_intelligence_asset.json",
        ],
        "decision_intelligence_asset": [
        "knowledge/factory/decision_intelligence/{concept}/**/*decision_intelligence_asset.json",
        "knowledge/factory/golden_concepts/{concept}/decision_intelligence_assets/**/*decision_intelligence_asset.json",
        "knowledge/factory/golden_concepts/{concept}/decision_intelligence/**/*decision_intelligence_asset.json",
        ],
    }

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root)

    def discover(self, concept_id: str) -> Dict[str, AssetRecord]:
        inventory: Dict[str, AssetRecord] = {}
        for asset_type, patterns in self.ASSET_PATTERNS.items():
            path, data = self._find_latest(concept_id, patterns)
            if path is None:
                inventory[asset_type] = AssetRecord(asset_type=asset_type, status="MISSING")
                continue
            inventory[asset_type] = AssetRecord(
                asset_type=asset_type,
                status="FOUND",
                path=str(path),
                certification_status = extract_certification_status(data),
                asset_id=str(data.get("asset_id") or data.get("package_id") or ""),
                summary=self._summarize(asset_type, data),
            )
        return inventory

    def _find_latest(self, concept_id: str, patterns: list[str]) -> Tuple[Optional[Path], dict]:
        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.repo_root.glob(pattern.format(concept=concept_id)))
        candidates = [p for p in candidates if p.is_file()]
        if not candidates:
            return None, {}
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        path = candidates[0]
        try:
            return path, json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return path, {}

    def _summarize(self, asset_type: str, data: dict) -> dict:
        if asset_type == "mental_model_asset":
            return {
                "current_model": data.get("current_mental_model", {}).get("belief"),
                "target_model": data.get("target_mental_model", {}).get("belief"),
                "transformation_type": data.get("transformation_plan", {}).get("transformation_type"),
            }
        if asset_type == "financial_outcome_asset":
            outcome = data.get("financial_outcome", {})
            return {
                "insurer_pays": outcome.get("insurer_pays"),
                "customer_pays": outcome.get("customer_pays"),
                "shock_level": outcome.get("financial_shock_level"),
            }
        return {"concept_id": data.get("concept_id"), "version": data.get("version")}
