from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any

from .asset_discovery_engine import AssetDiscoveryEngine
from .dependency_validator import DependencyValidator
from .consistency_engine import ConsistencyEngine
from .coverage_analyzer import CoverageAnalyzer
from .gap_analyzer import GapAnalyzer
from .certification_engine import PackageCertificationEngine
from .package_builder import GoldenConceptPackageBuilder


class GoldenConceptPackageAssembler:
    def __init__(self, repo_root: str | Path = ".", output_root: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.output_root = Path(output_root) if output_root else self.repo_root / "knowledge" / "factory" / "golden_concept_packages"

    def run(self, concept_id: str, concept_name: str | None = None) -> Dict[str, str]:
        concept_name = concept_name or concept_id.replace("_", " ").title()
        inventory = AssetDiscoveryEngine(self.repo_root).discover(concept_id)
        dependency = DependencyValidator().validate(inventory)
        consistency = ConsistencyEngine().check(inventory)
        coverage = CoverageAnalyzer().analyze(inventory)
        gaps = GapAnalyzer().analyze(inventory, coverage)
        # package id needs certification, certification needs package id; use temp id, then rebuild cert with final package id.
        temp_package = GoldenConceptPackageBuilder().build(
            concept_id, concept_name, inventory, consistency, coverage, gaps,
            PackageCertificationEngine().certify(concept_id, "pending", dependency, consistency, coverage.overall),
        )
        certification = PackageCertificationEngine().certify(concept_id, temp_package.package_id, dependency, consistency, coverage.overall)
        package = GoldenConceptPackageBuilder().build(concept_id, concept_name, inventory, consistency, coverage, gaps, certification)

        out_dir = self.output_root / concept_id
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "package": out_dir / f"{package.package_id}_golden_concept_package.json",
            "certification": out_dir / f"{certification.certification_id}_package_certification.json",
            "coverage": out_dir / f"{package.package_id}_coverage_analysis.json",
            "gaps": out_dir / f"{package.package_id}_gap_analysis.json",
        }
        self._write(paths["package"], package.to_dict())
        self._write(paths["certification"], asdict(certification))
        self._write(paths["coverage"], asdict(coverage))
        self._write(paths["gaps"], gaps)
        return {k: str(v) for k, v in paths.items()}

    def _write(self, path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
